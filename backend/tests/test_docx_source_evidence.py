"""Independent Office adapter regressions: real OOXML, no service/network calls."""

import hashlib
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

import docx
import pytest
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree
from PIL import Image

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_markdown import (
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document
from app.modules.knowledge.services.qnu_docx_artifacts import (
    build_qnu_markdown_artifact,
    rebuild_qnu_markdown_for_revision,
)
from app.modules.knowledge.services.qnu_serving import load_document
from app.modules.knowledge.services.source_extraction import SourceExtraction, extract_source
from app.modules.knowledge.services.source_purge import snapshot_paths

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PATH = "snapshots/collection/binding/fixture.docx"


def source(document, notes=()):
    stream = io.BytesIO()
    document.save(stream)
    original = ZipFile(io.BytesIO(stream.getvalue()))
    parts = {name: original.read(name) for name in original.namelist()}
    for kind in {kind for kind, _, _ in notes}:
        root = etree.Element(qn(f"w:{kind}s"), nsmap={"w": W})
        for part, key, text in notes:
            if part != kind:
                continue
            note = etree.SubElement(root, qn(f"w:{kind}"), {qn("w:id"): str(key)})
            paragraph = etree.SubElement(note, qn("w:p"))
            run = etree.SubElement(paragraph, qn("w:r"))
            etree.SubElement(run, qn("w:t")).text = text
        parts[f"word/{kind}s.xml"] = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
        rels = etree.fromstring(parts["word/_rels/document.xml.rels"])
        etree.SubElement(
            rels,
            "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
            Id=f"rId_{kind}s",
            Type=f"http://schemas.openxmlformats.org/officeDocument/2006/relationships/{kind}s",
            Target=f"{kind}s.xml",
        )
        parts["word/_rels/document.xml.rels"] = etree.tostring(rels)
        types = etree.fromstring(parts["[Content_Types].xml"])
        etree.SubElement(
            types,
            "{http://schemas.openxmlformats.org/package/2006/content-types}Override",
            PartName=f"/word/{kind}s.xml",
            ContentType=f"application/vnd.openxmlformats-officedocument.wordprocessingml.{kind}s+xml",
        )
        parts["[Content_Types].xml"] = etree.tostring(types)
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return stream.getvalue()


def anchor(paragraph, key=1, kind="footnote"):
    ref = OxmlElement(f"w:{kind}Reference")
    ref.set(qn("w:id"), str(key))
    paragraph.add_run()._r.append(ref)


def model(raw, split=None):
    parsed = DoclingOfficeParser("docx")._parse_sync(raw, "fixture.docx")
    cut = parsed.raw_text.index(split) if split else len(parsed.raw_text)
    ranges = [(1, 0, cut)] + ([(2, cut, len(parsed.raw_text))] if split else [])
    result = build_qnu_structured_document(
        parsed.docling_document,
        filename="fixture.docx",
        sha256=hashlib.sha256(raw).hexdigest(),
        header_evidence=parsed.docx_header_evidence,
        source_evidence=parsed.docx_source_evidence,
        projection_markdown=parsed.raw_text,
        page_ranges=ranges,
        render_page_count=len(ranges),
    )
    assert validate_qnu_markdown(
        render_qnu_markdown(result, document_id="binding", revision_id="revision")
    ).ok
    return parsed, result


def test_original_footnotes_endnotes_link_paragraph_and_table_rows():
    document = docx.Document()
    anchor(document.add_paragraph("A policy with a note."), 1)
    table = document.add_table(rows=2, cols=2)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    table.cell(0, 0).text, table.cell(0, 1).text = "Name", "Limit"
    table.cell(1, 0).text, table.cell(1, 1).text = "Alpha", "0"
    anchor(table.cell(1, 1).paragraphs[0], 2)
    anchor(document.add_paragraph("A separate exception."), 1, "endnote")
    _, result = model(
        source(
            document,
            [
                ("footnote", 1, "Only this policy."),
                ("footnote", 2, "Zero is measured."),
                ("endnote", 1, "Separate scope."),
            ],
        )
    )
    notes = [b for b in result.blocks if b.type == "note"]
    assert len(notes) == 3 and {b.body for b in notes} == {
        "Only this policy.",
        "Zero is measured.",
        "Separate scope.",
    }
    assert result.document_meta["source_inventory"]["linked_anchors"] == 3
    row = next(b for b in result.blocks if b.type == "table_row")
    note = next(b for b in notes if b.body == "Zero is measured.")
    assert row.context_refs == [note.id]
    assert note.attributes["source_anchors"][0]["table"]["column"] == 2
    assert "word/footnotes.xml" in note.source_locations[0].locator


def test_shared_note_is_directed_and_duplicate_paragraph_abstains():
    document = docx.Document()
    anchor(document.add_paragraph("First rule."), 4)
    anchor(document.add_paragraph("Second rule."), 4)
    _, result = model(source(document, [("footnote", 4, "A shared condition.")]))
    note = next(b for b in result.blocks if b.type == "note")
    assert len(note.attributes["source_anchors"]) == 2 and not note.context_refs
    document = docx.Document()
    anchor(document.add_paragraph("Same rule."), 4)
    document.add_paragraph("Same rule.")
    _, result = model(source(document, [("footnote", 4, "Do not guess the anchor.")]))
    note = next(b for b in result.blocks if b.type == "note")
    assert not note.attributes["source_anchors"]
    assert any(f.code == "source_note_unresolved" for f in note.quality_flags)


def test_missing_note_target_is_visible_without_invalid_context_ref():
    document = docx.Document()
    anchor(document.add_paragraph("A broken source reference."), 19)
    _, result = model(source(document))
    assert result.document_meta["source_inventory"]["missing_note_ids"] == ["footnote:19"]
    assert any(f.code == "source_note_missing" for b in result.blocks for f in b.quality_flags)
    assert all(not b.context_refs for b in result.blocks)


def test_caption_style_is_retained_without_guessing_prose_note_scope():
    document = docx.Document()
    document.add_paragraph("A caption with no explicit association.", style="Caption")
    _, result = model(source(document))
    block = next(b for b in result.blocks if "caption" in b.body)
    assert block.attributes["source_paragraph"]["style"] == ["Caption"]
    assert not block.context_refs


def test_vertical_header_alias_is_not_an_extra_hierarchy_level():
    document = docx.Document()
    table = document.add_table(rows=3, cols=2)
    for row in table.rows[:2]:
        row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    table.cell(0, 0).merge(table.cell(1, 0)).text = "Group"
    table.cell(0, 1).text, table.cell(1, 1).text = "2026", "Quota"
    table.cell(2, 0).text, table.cell(2, 1).text = "Alpha", "0"
    _, result = model(source(document))
    table = next(b for b in result.blocks if b.type == "table")
    assert [c["header_path"] for c in table.attributes["columns"]] == [["Group"], ["2026", "Quota"]]


def test_toc_prefix_does_not_make_real_heading_ambiguous():
    document = docx.Document()
    document.add_paragraph("Topic\t1")
    document.add_paragraph("A separator paragraph.")
    document.add_heading("Topic", 1)
    raw = source(document)
    parsed = DoclingOfficeParser("docx")._parse_sync(raw, "fixture.docx")
    heading = parsed.raw_text.rfind("# Topic")
    assert heading >= 0
    result = build_qnu_structured_document(
        parsed.docling_document,
        filename="fixture.docx",
        sha256="a" * 64,
        projection_markdown=parsed.raw_text,
        page_ranges=[(1, 0, heading), (2, heading, len(parsed.raw_text))],
    )
    block = next(b for b in result.blocks if b.type == "section")
    assert [loc.page for loc in block.source_locations] == [2]


def test_rich_cell_text_is_not_emitted_again_as_unrelated_prose():
    document = docx.Document()
    table = document.add_table(rows=2, cols=2)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    table.cell(0, 0).text, table.cell(0, 1).text = "Name", "Details"
    table.cell(1, 0).text = "Alpha"
    table.cell(1, 1).text = "A first preserved paragraph."
    table.cell(1, 1).add_paragraph("A second preserved paragraph.")
    _, result = model(source(document))
    assert not any(b.type == "text" and "preserved paragraph" in b.body for b in result.blocks)
    table = next(b for b in result.blocks if b.type == "table")
    assert "A first preserved paragraph." in str(table.source_data)
    assert "A second preserved paragraph." in str(table.source_data)


@pytest.mark.asyncio
async def test_image_archive_is_hash_bound_and_owned_by_snapshot_lifecycle():
    image = io.BytesIO()
    Image.new("RGB", (16, 16), "#126477").save(image, format="PNG")
    document = docx.Document()
    document.add_paragraph("A diagram.")
    document.add_picture(io.BytesIO(image.getvalue()))
    raw = source(document)
    parsed, result = model(raw)
    resource = parsed.docx_source_evidence["resources"][0]
    assert resource["data"] == image.getvalue()
    stored = {}

    async def save(path, data):
        stored[path] = data

    storage = SimpleNamespace(
        save=AsyncMock(side_effect=save),
        exists=AsyncMock(side_effect=lambda p: p in stored),
        get=AsyncMock(side_effect=lambda p: stored.get(p)),
    )
    extraction = SourceExtraction("", 1, qnu_document=result, office_resources=[resource])
    with (
        patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service", storage),
        patch("app.modules.knowledge.services.qnu_serving.storage_service", storage),
    ):
        artifact = await build_qnu_markdown_artifact(
            extraction=extraction,
            document_id="binding",
            revision_id="revision",
            title=None,
            snapshot_path=PATH,
        )
        assert artifact["status"] == "ready"
        loaded = await load_document(
            artifact,
            binding_id="binding",
            revision_id="revision",
            origin_hash=hashlib.sha256(raw).hexdigest(),
            snapshot_path=PATH,
        )
        figure = next(b for b in loaded.blocks if b.type == "figure")
        manifest = artifact["raw_evidence"]
        with ZipFile(io.BytesIO(stored[manifest["path"]])) as archive:
            assert archive.read(figure.attributes["resource"]["archive_member"]) == image.getvalue()
        rev = SimpleNamespace(
            snapshot_storage_path=PATH,
            snapshot_metadata={"qnu_markdown": artifact},
            parse_provenance={},
        )
        assert manifest["path"] in snapshot_paths(rev)
        assert any(f.code == "figure_content_unverified" for f in figure.quality_flags)
        assert not any(f.code == "missing_content" for f in figure.quality_flags)
        stored[manifest["path"]] = b"tampered"
        with pytest.raises(AppException):
            await load_document(
                artifact,
                binding_id="binding",
                revision_id="revision",
                origin_hash=hashlib.sha256(raw).hexdigest(),
                snapshot_path=PATH,
            )
        rebuilt = await rebuild_qnu_markdown_for_revision(
            artifact, document_id="binding", revision_id="revision2", snapshot_path=PATH
        )
        assert rebuilt["status"] == "failed"


@pytest.mark.asyncio
async def test_resource_failure_never_returns_ready_standard():
    document = docx.Document()
    document.add_paragraph("No live storage writes.")
    _, result = model(source(document))
    extraction = SourceExtraction(
        "",
        1,
        qnu_document=result,
        office_resources=[{"data": b"bad", "sha256": "a" * 64, "member": "word/media/image.png"}],
    )
    artifact = await build_qnu_markdown_artifact(
        extraction=extraction,
        document_id="binding",
        revision_id="revision",
        title=None,
        snapshot_path=PATH,
    )
    assert artifact["status"] == "failed" and artifact["reason"] == "office_resource_save_failed"


@pytest.mark.asyncio
async def test_office_inventory_rejects_lost_note_before_any_storage_write():
    document = docx.Document()
    anchor(document.add_paragraph("A preserved rule."))
    _, result = model(source(document, [("footnote", 1, "A required condition.")]))
    result.blocks = [block for block in result.blocks if block.type != "note"]
    storage = SimpleNamespace(save=AsyncMock(), exists=AsyncMock(return_value=False))
    with patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service", storage):
        artifact = await build_qnu_markdown_artifact(
            extraction=SourceExtraction("", 1, qnu_document=result),
            document_id="binding",
            revision_id="revision",
            title=None,
            snapshot_path=PATH,
        )
    assert artifact["status"] == "failed"
    storage.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_extraction_passes_original_anchors_and_render_location():
    document = docx.Document()
    anchor(document.add_paragraph("A source paragraph."))
    raw = source(document, [("footnote", 1, "A uniquely located note.")])
    parsed = DoclingOfficeParser("docx")._parse_sync(raw, "fixture.docx")
    rendered = SourceExtraction(
        parsed.raw_text,
        1,
        pages=[
            {
                "page_number": 1,
                "extracted_text": parsed.raw_text,
                "alignment_text": parsed.raw_text + "\nA uniquely located note.",
                "engine_used": "native",
            }
        ],
    )
    with (
        patch(
            "app.modules.knowledge.services.ingestion_service.IngestionService._convert_office_to_pdf",
            AsyncMock(return_value=b"preview"),
        ),
        patch(
            "app.modules.knowledge.services.source_extraction.extract_pdf",
            AsyncMock(return_value=rendered),
        ),
    ):
        result = await extract_source(
            AsyncMock(), raw, "fixture.docx", "docx", "standard", None, "tenant_qnu"
        )
    note = next(b for b in result.qnu_document.blocks if b.type == "note")
    assert note.source_locations[0].page == 1
    assert result.qnu_document.document_meta["source_inventory"]["linked_anchors"] == 1
