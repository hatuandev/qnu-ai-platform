"""Unshaded PDF headers and cropped OCR fields require independent source evidence."""
import copy
import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pymupdf
import pytest

from app.modules.knowledge.normalization.qnu_markdown import (
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.parsers.pdf_evidence import capture_native_page
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document
from app.modules.knowledge.services.header_rescue import rescue_header


def add_grid(page, *, multi=False, header=True, bold_data=False, top=45, tall=True):
    xs = [40, 140, 240, 340]
    ys = [top, top + 26, top + 52] if multi else [top, top + (34 if tall else 20)]
    ys += [ys[-1] + 20 * i for i in (1, 2, 3)]
    if not header:
        ys = [top + 20 * i for i in range(5)]
    for row, y in enumerate(ys):
        page.draw_line((xs[1] if multi and row == 1 else xs[0], y), (xs[-1], y))
    for index, x in enumerate(xs):
        page.draw_line((x, ys[1] if multi and index == 2 else ys[0]), (x, ys[-1]))
    def text(value, col, row, *, bold=False, end_col=None, end_row=None, centered=False):
        right, bottom = xs[end_col or col + 1], ys[end_row or row + 1]
        font = 'hebo' if bold else 'helv'
        width = pymupdf.get_text_length(value, fontname=font, fontsize=9)
        x = (xs[col] + right - width) / 2 if centered else xs[col] + 8
        page.insert_text((x, (ys[row] + bottom) / 2 + 3), value, fontsize=9, fontname=font)

    depth = (2 if multi else 1) if header else 0
    if header:
        if multi:
            text('Ref', 0, 0, bold=True, end_row=2, centered=True)
            text('2034', 1, 0, bold=True, end_col=3, centered=True)
            text('Measure', 1, 1, bold=True, centered=True)
            text('Band', 2, 1, bold=True, centered=True)
        else:
            for c, value in enumerate(['Ref', 'Measure', 'Band']):
                text(value, c, 0, bold=True, centered=True)
    values = [['0007', '0', 'North'], ['B-19', '95.8', 'South'], ['Z-2', '6', 'East']]
    if not header:
        values.insert(0, ['Alpha', 'North', '0'])
    for r, values_row in enumerate(values, depth):
        for c, value in enumerate(values_row):
            text(value, c, r, bold=bold_data and r == 0)
    return depth


def build(pdf):
    source = {'pages': [{'page': p.number + 1, 'native': capture_native_page(p)} for p in pdf]}
    return build_pdf_document(source, filename='generated.pdf', sha256='a' * 64)


@pytest.mark.parametrize('multi', [False, True])
def test_white_header_has_column_paths_and_preserves_first_data_record(multi):
    with pymupdf.open() as pdf:
        add_grid(pdf.new_page(width=400, height=350), multi=multi)
        document = build(pdf)
    table = next(b for b in document.blocks if b.type == 'table')
    rows = [b for b in document.blocks if b.type == 'table_row']
    assert table.source_data['table']['header_depth'] == (2 if multi else 1)
    assert [c['header_path'] for c in table.attributes['columns']] == (
        [['Ref'], ['2034', 'Measure'], ['2034', 'Band']] if multi else [['Ref'], ['Measure'], ['Band']])
    assert len(rows) == 3
    assert [r.attributes['fields']['c01']['raw'] for r in rows] == ['0007', 'B-19', 'Z-2']
    assert rows[0].attributes['fields']['c02']['raw'] == '0'
    assert rows[0].attributes['fields']['c02']['state'] == 'present'
    assert validate_qnu_markdown(render_qnu_markdown(document, document_id='b', revision_id='r')).ok


@pytest.mark.parametrize('bold_first', [False, True])
def test_white_headerless_grid_does_not_consume_styled_first_data(bold_first):
    with pymupdf.open() as pdf:
        add_grid(pdf.new_page(), header=False, bold_data=bold_first)
        document = build(pdf)
    table = next(b for b in document.blocks if b.type == 'table')
    rows = [b for b in document.blocks if b.type == 'table_row']
    assert table.source_data['table']['header_depth'] == 0
    assert len(rows) == 4
    assert rows[0].attributes['fields']['c01']['raw'] == 'Alpha'
    assert rows[0].attributes['fields']['c02']['raw'] == 'North'
    assert all(r.attributes['interpretation'] == 'literal_only' for r in rows)


@pytest.mark.parametrize('new_caption', [False, True])
def test_white_header_continuation_needs_matching_structure_and_no_new_scope(new_caption):
    with pymupdf.open() as pdf:
        add_grid(pdf.new_page(width=400, height=240), top=130)
        page = pdf.new_page(width=400, height=240)
        if new_caption:
            page.insert_text((40, 15), 'Different scope')
        add_grid(page, top=30)
        document = build(pdf)
    tables = [b for b in document.blocks if b.type == 'table']
    assert len(tables) == 2
    assert bool(tables[1].attributes.get('continuation')) is not new_caption
    assert len([b for b in document.blocks if b.type == 'table_row']) == 6


def test_merged_header_cannot_absorb_a_bold_first_body_row():
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=400, height=350)
        add_grid(page, multi=True)
        raw = capture_native_page(page)
        table = raw['tables'][0]
        body_boxes = [box for box in table['cell_boxes'][2] if box]
        for block in raw['layout']['blocks']:
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    center = (span['bbox'][1] + span['bbox'][3]) / 2
                    if any(box[1] <= center <= box[3] for box in body_boxes):
                        span['flags'] |= 16
        from app.modules.knowledge.parsers.pdf_header_roles import header_role_evidence

        table['header_evidence'] = header_role_evidence(table, raw['layout'], raw['drawings'])
        document = build_pdf_document({'pages': [{'page': 1, 'native': raw}]},
                                      filename='generated.pdf', sha256='a' * 64)
    rows = [b for b in document.blocks if b.type == 'table_row']
    assert any(r.attributes['fields']['c01']['raw'] == '0007' for r in rows)
    assert table['header_evidence'].get('depth', 0) <= 2


@pytest.mark.parametrize('forged', [False, True])
def test_saved_v5_evidence_remains_verifiable_without_upgrading_header_roles(forged):
    from app.modules.knowledge.parsers.pdf_fidelity import verify_pdf_source
    from app.modules.knowledge.parsers.pdf_header_roles import header_role_evidence

    with pymupdf.open() as pdf:
        add_grid(pdf.new_page(), multi=True)
        payload = pdf.tobytes()
        raw = capture_native_page(pdf[0])
    evidence = {'source_sha256': hashlib.sha256(payload).hexdigest(), 'pages': [{'page': 1, 'native': raw}]}
    if forged:
        raw['tables'][0]['header_evidence'] = header_role_evidence(raw['tables'][0], raw['layout'], raw['drawings'])
    else:
        raw['tables'][0]['header_evidence'] = {}
    document = build_pdf_document(evidence, filename='legacy.pdf', sha256=evidence['source_sha256'])
    document.document_meta['builder_version'] = 'pdf-evidence-structure/v5'
    saved = copy.deepcopy(document.model_dump())
    if forged:
        with pytest.raises(ValueError, match='PDF_NATIVE_EVIDENCE_MISMATCH'):
            verify_pdf_source(document, payload, evidence)
    else:
        verify_pdf_source(document, payload, evidence)
    assert document.model_dump() == saved


def add_numbered_grid(page, start, *, header=False, caption=False, shifted=False):
    xs = [40, 140, 240, 340] if not shifted else [40, 125, 260, 340]
    top = 100 if header else 10
    heights = [30, 20, 20, 20, 20] if header else [20] * 4
    ys = [top]
    for height in heights:
        ys.append(ys[-1] + height)
    if caption:
        page.insert_text((40, 7), 'New scope', fontsize=5)
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    for x in xs:
        page.draw_line((x, top), (x, ys[-1]))
    values = [[str(n), f'Item {n}', str(n * 3)] for n in range(start, start + 4)]
    if header:
        values.insert(0, ['Position', 'Entry', 'Measure'])
    for row, cells in enumerate(values):
        for col, value in enumerate(cells):
            font = 'hebo' if header and row == 0 else 'helv'
            x = xs[col] + 8
            if header and row == 0:
                x = (xs[col] + xs[col + 1] - pymupdf.get_text_length(value, fontname=font, fontsize=9)) / 2
            page.insert_text((x, (ys[row] + ys[row + 1]) / 2 + 3), value, fontname=font, fontsize=9)


@pytest.mark.parametrize('reason', ['none', 'caption', 'gap', 'axes'])
def test_headerless_continuation_requires_unique_geometry_and_contiguous_source_sequence(reason):
    with pymupdf.open() as pdf:
        add_numbered_grid(pdf.new_page(width=400, height=220), 1, header=True)
        add_numbered_grid(pdf.new_page(width=400, height=220), 5 if reason != 'gap' else 6,
                          caption=reason == 'caption', shifted=reason == 'axes')
        document = build(pdf)
    tables = [b for b in document.blocks if b.type == 'table']
    rows = [b for b in document.blocks if b.type == 'table_row' and b.parent_id == tables[1].id]
    assert len(rows) == 4
    assert rows[0].attributes['fields']['c01']['raw'] == ('6' if reason == 'gap' else '5')
    if reason == 'none':
        assert tables[1].attributes['columns'] == tables[0].attributes['columns']
        assert tables[1].attributes['inherited_header']['block_id'] == tables[0].id
        assert tables[1].attributes['continuation']['status'] == 'verified'
        assert rows[0].attributes['fields']['c03']['state'] == 'present'
        assert not any(f.status == 'unresolved' and f.code in {
            'native_header_needs_review', 'table_header_unresolved', 'table_continuation_needs_review'}
            for f in tables[1].quality_flags)
    else:
        assert 'inherited_header' not in tables[1].attributes
        assert rows[0].attributes['interpretation'] == 'literal_only'


def test_three_headerless_fragments_keep_each_pages_cells_and_header_lineage():
    with pymupdf.open() as pdf:
        # Each continued fragment reaches the next page boundary.
        for page_no, start in enumerate([1, 5, 9]):
            page = pdf.new_page(width=400, height=220 if page_no == 0 else 95)
            add_numbered_grid(page, start, header=page_no == 0)
        document = build(pdf)
    tables = [b for b in document.blocks if b.type == 'table']
    assert len(tables) == 3 and len([b for b in document.blocks if b.type == 'table_row']) == 12
    assert tables[2].attributes['inherited_header']['block_id'] == tables[1].id
    assert tables[2].attributes['columns'] == tables[0].attributes['columns']
    assert tables[2].source_data['table']['header_depth'] == 0  # No printed header was invented.


def ocr_block(text, *, coords=None, kind='header', block_id='header-4'):
    return {'id': block_id, 'type': kind, 'text': text,
            'coordinates': coords if coords is not None else
                {'left': 5, 'top': 5, 'width': 40, 'height': 15, 'is_valid': True}}


async def rescue(blocks, *, markdown='Gia Lai, ngày 03 tháng 8 năm 2028', native=None):
    page = {'page_number': 1, 'extracted_text': native or 'Số: /TB-XX\nGia Lai, ngày tháng năm 2028\nOriginal body',
            'engine_used': 'native'}
    prepared = {'content': b'crop', 'missing': ['document_number', 'issued_date'], 'bbox': [0, 0, 500, 200]}
    response = SimpleNamespace(success=True, engine_used='paddleocr_vl', raw_evidence={'retained': True},
        pages=[SimpleNamespace(extracted_text=markdown, blocks=blocks)])
    with patch('app.modules.knowledge.services.header_rescue.OCRService.extract_document',
               AsyncMock(return_value=response)) as call:
        await rescue_header(AsyncMock(), page, prepared, 'paddleocr', 'test')
    assert call.call_count == 1
    return page


@pytest.mark.asyncio
async def test_header_rescue_uses_located_blocks_omitted_by_ocr_markdown():
    page = await rescue([ocr_block('Số: 408 /TB-XX')])
    audit = page['metadata_rescue']
    assert audit['status'] == 'proposed'
    assert audit['accepted_lines'] == ['Số: 408/TB-XX', 'Gia Lai, ngày 03 tháng 8 năm 2028']
    assert page['extracted_text'].endswith('Original body')
    assert audit['field_sources']['document_number'][0]['block_id'] == 'header-4'
    assert page['_header_raw_evidence'] == {'retained': True}


@pytest.mark.asyncio
@pytest.mark.parametrize('coords', [
    {}, {'left': -1, 'top': 5, 'width': 40, 'height': 15, 'is_valid': True},
    {'left': 5, 'top': 5, 'width': 0, 'height': 15, 'is_valid': True},
    {'left': 95, 'top': 5, 'width': 40, 'height': 15, 'is_valid': True},
    {'left': 5, 'top': 5, 'width': 40, 'height': 15, 'is_valid': False},
    {'left': float('nan'), 'top': 5, 'width': 40, 'height': 15, 'is_valid': True},
    {'left': 5, 'top': 5, 'width': 40, 'height': 15, 'is_valid': True, 'coordinate_system': 'pixels'},
])
async def test_unlocated_or_invalid_ocr_blocks_cannot_supply_header_fields(coords):
    page = await rescue([ocr_block('Số: 408/TB-XX', coords=coords)])
    assert '408' not in page['extracted_text']
    assert page['metadata_rescue']['status'] == 'incomplete'


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['table', 'figure', 'formula', 'footer'])
async def test_non_header_content_roles_cannot_inject_header_fields(kind):
    page = await rescue([ocr_block('Số: 408/TB-XX', kind=kind)])
    assert '408' not in page['extracted_text']


@pytest.mark.asyncio
async def test_duplicate_same_field_is_idempotent_and_conflicting_fields_are_not_selected():
    repeated = await rescue([ocr_block('Số: 408/TB-XX'), ocr_block('Số: 408 /TB-XX', block_id='header-5')])
    assert repeated['metadata_rescue']['accepted_lines'].count('Số: 408/TB-XX') == 1
    conflicting = await rescue([ocr_block('Số: 408/TB-XX'), ocr_block('Số: 409/TB-XX', block_id='header-5')])
    assert '408' not in conflicting['extracted_text'] and '409' not in conflicting['extracted_text']
    assert conflicting['metadata_rescue']['status'] == 'incomplete'


@pytest.mark.asyncio
async def test_markdown_and_raw_block_conflict_cannot_silently_prefer_one():
    page = await rescue([ocr_block('Số: 409/TB-XX')], markdown='Số: 408/TB-XX\nGia Lai, ngày 03 tháng 8 năm 2028')
    assert '408' not in page['extracted_text'] and '409' not in page['extracted_text']
    assert page['metadata_rescue']['status'] == 'incomplete'


@pytest.mark.asyncio
async def test_ocr_field_still_cannot_override_an_existing_native_field():
    page = await rescue([ocr_block('Số: 409/TB-XX')], native='Số: 408/TB-XX\nOriginal body')
    assert page['extracted_text'] == 'Số: 408/TB-XX\nOriginal body'
    assert page['metadata_rescue']['status'] == 'conflict'


def test_legacy_v5_read_does_not_inherit_new_continuation_semantics():
    from app.modules.knowledge.parsers.pdf_fidelity import verify_pdf_source

    with pymupdf.open() as pdf:
        page = pdf.new_page(width=400, height=220)
        add_numbered_grid(page, 1, header=True)
        page.draw_rect((40, 100, 340, 130), color=None, fill=(.8, .9, .95), overlay=False)
        add_numbered_grid(pdf.new_page(width=400, height=220), 5)
        payload = pdf.tobytes()
        evidence = {'source_sha256': hashlib.sha256(payload).hexdigest(), 'pages': [
            {'page': p.number + 1, 'native': capture_native_page(p, allow_unshaded_headers=False)} for p in pdf]}
    document = build_pdf_document(evidence, filename='old.pdf', sha256=evidence['source_sha256'], legacy_v5=True)
    document.document_meta['builder_version'] = 'pdf-evidence-structure/v5'
    tables = [b for b in document.blocks if b.type == 'table']
    assert tables[0].source_data['table']['header_depth'] == 1
    assert 'inherited_header' not in tables[1].attributes
    before = copy.deepcopy(document.model_dump())
    verify_pdf_source(document, payload, evidence)
    assert document.model_dump() == before


@pytest.mark.parametrize('location,body,removed', [
    ([40, 100, 340, 120], '5 Item 5 15', True),
    ([40, 100, 340, 120], '5 Item 5 1', False),
    ([40, 80, 340, 99], '5 Item 5 15', False),
])
def test_native_duplicate_projection_requires_complete_cells_and_source_geometry(location, body, removed):
    from app.modules.knowledge.normalization.qnu_markdown import QnuBlock, QnuSourceLocation
    from app.modules.knowledge.parsers.pdf_continuations import retain_native_projections

    with pymupdf.open() as pdf:
        add_numbered_grid(pdf.new_page(width=400, height=220), 1, header=True)
        document = build(pdf)
    table = next(b for b in document.blocks if b.type == 'table')
    # A merged group cell is independently present in the grid but not this text block.
    table.source_data['table']['raw_native'] = {'bbox': [40, 100, 340, 120],
        'matrix': [['5', 'Group', 'Item 5', '15']],
        'cell_boxes': [[[40, 100, 80, 120], [80, 100, 120, 120], [120, 100, 280, 120], [280, 100, 340, 120]]]}
    table.attributes['native_literal_coverage'] = {'status': 'verified'}
    text = QnuBlock(id='projection', type='text', body=body, attributes={'engine_used': 'native'},
        source_locations=[QnuSourceLocation(page=1, locator='native/text/1')], source_data={'raw': {'bbox': location}})
    blocks = [table, text]
    retain_native_projections(blocks)
    assert (text not in blocks) is removed
    if removed:
        audit = table.source_data['native_text_projections'][0]
        assert [cell['column'] for cell in audit['cells']] == [0, 2, 3]
        assert audit['raw']['bbox'] == location
