from io import BytesIO

import pytest
from docx import Document
from docx.oxml import OxmlElement

from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.parsers.docling_structure import (
    build_qnu_structured_document,
    map_unit_to_page,
)
from app.modules.knowledge.parsers.docx_layout_fidelity import (
    preserve_native_layout,
    verify_native_layout,
)


async def native_model(*, header=False, merge=False):
    document = Document()
    table = document.add_table(rows=3, cols=2)
    for row, values in zip(table.rows, [('Alpha', 'North'), ('2', 'South'), ('0', 'East')], strict=True):
        for cell, value in zip(row.cells, values, strict=True):
            cell.text = value
    if header:
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    if merge:
        table.rows[1].cells[0].merge(table.rows[1].cells[1]).text = 'Shared literal 42'
    out = BytesIO()
    document.save(out)
    raw = out.getvalue()
    parsed = await get_document_parser('docx').parse(raw, 'unrelated.docx')
    model = build_qnu_structured_document(parsed.docling_document, filename='unrelated.docx', sha256=__import__('hashlib').sha256(raw).hexdigest(),
        header_evidence=parsed.docx_header_evidence, source_evidence=parsed.docx_source_evidence)
    return model, raw


async def test_untyped_source_grid_is_literal_only_never_promotes_alpha_to_header():
    model, raw = await native_model()
    preserve_native_layout(model, raw)
    table = next(b for b in model.blocks if b.type == 'table')
    rows = [b for b in model.blocks if b.type == 'table_row']
    assert table.attributes['column_roles'] == 'unknown'
    assert len(rows) == 3 and rows[0].attributes['fields']['c01']['raw'] == 'Alpha'
    assert all(f['state'] == 'ambiguous' for b in rows for f in b.attributes['fields'].values())
    flags = [f for f in table.quality_flags if f.code == "table_header_unresolved"]
    assert len(flags) == 1 and flags[0].status == "confirmed"
    verify_native_layout(model, raw)
    _, artifact = project_document(model, {'structured_sha256': 'a' * 64}, {})
    assert not artifact['facts']


async def test_source_merge_stays_one_literal_without_assigning_group_scope():
    model, raw = await native_model(header=True, merge=True)
    preserve_native_layout(model, raw)
    row = next(b for b in model.blocks if b.type == 'table_row' and b.source_label == '2')
    assert row.attributes['row_role'] == 'source_merged_literal'
    assert row.body == 'Shared literal 42'
    assert row.context_refs == []
    assert all(f['state'] == 'ambiguous' for f in row.attributes['fields'].values())
    assert not row.quality_flags
    verify_native_layout(model, raw)


async def test_wrong_source_does_not_resolve_any_flag():
    model, _ = await native_model()
    _, other = await native_model(header=True)
    preserve_native_layout(model, other)
    assert any(f.code == 'table_header_unresolved' for b in model.blocks for f in b.quality_flags)
    assert not any('native_layout' in b.attributes for b in model.blocks)


async def test_tampered_field_fails_revalidation():
    model, raw = await native_model()
    preserve_native_layout(model, raw)
    next(b for b in model.blocks if b.type == 'table_row').attributes['fields']['c01']['raw'] = '999'
    with pytest.raises(ValueError):
        verify_native_layout(model, raw)


async def test_missing_raw_row_is_not_certified():
    model, raw = await native_model()
    model.blocks.remove(next(b for b in model.blocks if b.type == 'table_row'))
    preserve_native_layout(model, raw)
    assert any(f.code == 'table_header_unresolved' for b in model.blocks for f in b.quality_flags)
    assert all(f.status == 'unresolved' for b in model.blocks for f in b.quality_flags
               if f.code == 'table_header_unresolved')


async def test_header_role_does_not_disambiguate_identical_native_table_content():
    from app.modules.knowledge.parsers.docx_layout_fidelity import _matched_table, _native

    model, raw = await native_model()
    table = next(b for b in model.blocks if b.type == 'table')
    rows = [b for b in model.blocks if b.type == 'table_row']
    native = _native(raw)
    native.append({**native[0], 'header_rows': 1, 'locator': 'word/document.xml/table/2'})
    assert _matched_table(table, native, rows) is None


async def test_explicit_header_keeps_data_values_present():
    model, raw = await native_model(header=True)
    preserve_native_layout(model, raw)
    assert all(f['state'] == 'present' for b in model.blocks if b.type == 'table_row' for f in b.attributes['fields'].values())


def test_quoted_list_content_maps_after_number_and_opening_quote():
    text = '7. “Some programme” has code 0042.\n'
    pages, _, state = map_unit_to_page('“Some programme” has code 0042.', [(1, 0, len(text))], 0, text, full_lines=True)
    assert pages == [1] and state == 'matched'


def test_prose_prefix_is_not_a_standalone_list_item():
    text = 'Quoted elsewhere: Some programme has code 0042.\n'
    pages, _, _ = map_unit_to_page('Some programme has code 0042.', [(1, 0, len(text))], 0, text, full_lines=True)
    assert not pages


async def test_native_literal_restrictions_survive_standard_artifact_roundtrip():
    from app.modules.knowledge.services.qnu_docx_artifacts import build_qnu_markdown_artifact
    from app.modules.knowledge.services.qnu_serving import load_document
    from app.modules.knowledge.services.source_extraction import SourceExtraction

    model, raw = await native_model()
    preserve_native_layout(model, raw)
    artifact = await build_qnu_markdown_artifact(
        extraction=SourceExtraction(raw_text='Source table', page_count=1, qnu_document=model),
        document_id='binding_native_roundtrip', revision_id='revision_native_roundtrip',
        title=None, snapshot_path='test-native-roundtrip/source.docx',
    )
    assert artifact['status'] == 'ready', artifact.get('validation')
    restored = await load_document(
        artifact, binding_id='binding_native_roundtrip', revision_id='revision_native_roundtrip',
        origin_hash=model.source.sha256, snapshot_path='test-native-roundtrip/source.docx',
    )
    verify_native_layout(restored, raw)
    table = next(b for b in restored.blocks if b.type == 'table')
    assert table.attributes['column_roles'] == 'unknown'
    assert any(f.code == 'table_header_unresolved' and f.status == 'confirmed'
               for f in table.quality_flags)
    rows = [b for b in restored.blocks if b.type == 'table_row']
    assert [[f['raw'] for f in b.attributes['fields'].values()] for b in rows] == [
        ['Alpha', 'North'], ['2', 'South'], ['0', 'East'],
    ]
    assert all(b.attributes['interpretation'] == 'literal_only' for b in rows)
    assert all(f['state'] == 'ambiguous' and f['normalized'] is None
               for b in rows for f in b.attributes['fields'].values())
    _, artifact = project_document(restored, {'structured_sha256': 'a' * 64}, {})
    assert not artifact['facts']
    assert not any(issue['code'] == 'table_header_unresolved' for issue in artifact['issues'])
