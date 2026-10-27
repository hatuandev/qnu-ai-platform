"""PDF drawing primitives must preserve cells, header roles and QNU Markdown."""

from __future__ import annotations

import pymupdf
import pytest

from app.modules.knowledge.normalization.qnu_markdown import (
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.parsers.pdf_evidence import capture_native_page
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document


def shaded_table(*, columns=3, body_shading=False, bold=True, shading=True):
    """Word-style fill-only borders, merged header and inset paragraph backgrounds."""
    doc = pymupdf.open()
    page = doc.new_page(width=550, height=400)
    xs = [40 + 100 * i for i in range(columns + 1)]
    ys = [40, 65, 90, 115, 140, 165]
    band = (0.85, 0.9, 0.95)

    def cell(c0, c1, r0, r1, text, header=False, fill=None):
        box = pymupdf.Rect(xs[c0], ys[r0], xs[c1], ys[r1])
        if fill is not None:
            page.draw_rect(box, color=None, fill=fill)
            page.draw_rect((box.x0 + 5, box.y0 + 5, box.x1 - 5, box.y1 - 5), color=None, fill=fill)
        page.insert_text((box.x0 + 9, box.y0 + 16), text,
                         fontname="hebo" if header and bold else "helv", fontsize=9)

    cell(0, 1, 0, 2, "Ref", True, band if shading else None)
    cell(1, columns, 0, 1, "2031", True, band if shading else None)
    for c in range(1, columns):
        cell(c, c + 1, 1, 2, f"Measure {c}", True, band if shading else None)
    for r, code in enumerate(["0012", "AM-0070", "Z9"], 2):
        for c in range(columns):
            value = code if c == 0 else ["0", "95,8", "-"][r - 2]
            cell(c, c + 1, r, r + 1, value,
                 fill=(0.94, 0.94, 0.94) if body_shading and r == 3 else None)
    # Border strokes are thin filled rectangles, as in common Office PDF exports.
    for y in ys:
        page.draw_rect((xs[0], y - .24, xs[-1], y + .24), color=None, fill=(.4, .4, .4))
    for c, x in enumerate(xs):
        top = ys[1] if 1 < c < columns else ys[0]
        page.draw_rect((x - .24, top, x + .24, ys[-1]), color=None, fill=(.4, .4, .4))
    # Genuine artwork away from the table must not disappear with table furniture.
    page.draw_rect((60, 240, 170, 290), color=(0, 0, 0), fill=(.4, .7, .2))
    return doc


def build(page):
    raw = capture_native_page(page)
    doc = build_pdf_document({"pages": [{"page": 1, "native": raw}]},
                             filename="generated.pdf", sha256="a" * 64)
    return raw, doc


@pytest.mark.parametrize("columns,body_shading", [(3, False), (4, True)])
def test_shaded_pdf_keeps_logical_cells_and_multilevel_header(columns, body_shading):
    with shaded_table(columns=columns, body_shading=body_shading) as pdf:
        raw, doc = build(pdf[0])
    table = next(b for b in doc.blocks if b.type == "table")
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert len(table.attributes["columns"]) == columns
    assert len(rows) == 3
    assert [c["header_path"] for c in table.attributes["columns"]] == [
        ["Ref"], *[["2031", f"Measure {c}"] for c in range(1, columns)]]
    assert [r.attributes["fields"]["c01"]["raw"] for r in rows] == ["0012", "AM-0070", "Z9"]
    assert rows[0].attributes["fields"]["c02"]["raw"] == "0"
    assert rows[1].attributes["fields"]["c02"]["raw"] == "95,8"
    assert rows[2].attributes["fields"]["c02"]["state"] == "ambiguous"
    assert all(r.attributes["field_sources"]["c02"]["bbox"] for r in rows)
    assert raw["drawings"]  # No graphics evidence is discarded.
    assert raw["tables"][0]["geometry"]["original_candidates"]
    assert not any(f.code in {"native_header_needs_review", "table_header_unresolved"} for f in table.quality_flags)
    assert len([b for b in doc.blocks if b.type == "figure"]) == 1
    assert validate_qnu_markdown(render_qnu_markdown(doc, document_id="b", revision_id="r")).ok


@pytest.mark.parametrize("bold,shading", [(False, True), (True, False), (False, False)])
def test_styling_without_independent_header_evidence_keeps_every_row(bold, shading):
    with shaded_table(bold=bold, shading=shading) as pdf:
        _, doc = build(pdf[0])
    table = next(b for b in doc.blocks if b.type == "table")
    if bold and not shading:
        # White fill is no longer required when independent merged parent/child
        # boundaries plus the bounded typography contrast establish both levels.
        assert [c['header_path'] for c in table.attributes['columns']] == [
            ['Ref'], ['2031', 'Measure 1'], ['2031', 'Measure 2']]
        assert [b.attributes['fields']['c01']['raw'] for b in doc.blocks if b.type == 'table_row'] == [
            '0012', 'AM-0070', 'Z9']
        return
    assert len([b for b in doc.blocks if b.type == "table_row"]) == 5
    assert all(not c["header_path"] for c in table.attributes["columns"])
    assert any(f.code == "table_header_unresolved" for f in table.quality_flags)


def test_headerless_numeric_pdf_keeps_first_data_row():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for y in [50, 80, 110]:
            page.draw_line((50, y), (250, y))
        for x in [50, 150, 250]:
            page.draw_line((x, 50), (x, 110))
        for y, row in [(70, ["Alpha", "North"]), (100, ["2", "South"])]:
            for x, text in zip([60, 160], row, strict=True):
                page.insert_text((x, y), text)
        _, doc = build(page)
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert rows[0].attributes["fields"]["c02"]["raw"] == "North"


def test_fill_only_table_is_not_lost_beside_a_ruled_table():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for y in [40, 70, 100]:
            page.draw_line((40, y), (240, y))
        for x in [40, 140, 240]:
            page.draw_line((x, 40), (x, 100))
        for row in range(2):
            for col in range(2):
                page.insert_text((50 + col * 100, 60 + row * 30), f"R{row}{col}")
                box = pymupdf.Rect(40 + col * 100, 200 + row * 30, 140 + col * 100, 230 + row * 30)
                page.draw_rect(box, color=None, fill=(.8, .9, .8))
                page.insert_text((box.x0 + 10, box.y0 + 20), f"F{row}{col}")
        raw, doc = build(page)
    assert len(raw["tables"]) == 2
    assert any(t["geometry"]["status"] == "unresolved" for t in raw["tables"])
    fields = [f["raw"] for b in doc.blocks if b.type == "table_row" for f in b.attributes["fields"].values()]
    assert set(fields) >= {"R00", "R01", "R10", "R11", "F00", "F01", "F10", "F11"}


def test_single_column_table_preserves_zero_and_identifier_rows():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.draw_rect((50, 50, 350, 80), color=None, fill=(.8, .9, .95))
        for y in [50, 80, 110, 140, 170]:
            page.draw_line((50, y), (350, y))
        for x in [50, 350]:
            page.draw_line((x, 50), (x, 170))
        for i, text in enumerate(["Trace", "0", "00027", "Undeclared"]):
            page.insert_text((60, 70 + 30 * i), text, fontname="hebo" if i == 0 else "helv")
        # A separate full-width spanning row must not join the first table across a gap.
        for y in [240, 270, 300]:
            page.draw_line((50, y), (350, y))
        for x in [50, 200, 350]:
            page.draw_line((x, 240), (x, 300))
        page.insert_text((60, 260), "Other")
        raw, doc = build(page)
    one = next(b for b in doc.blocks if b.type == "table" and len(b.attributes["columns"]) == 1)
    rows = [b for b in doc.blocks if b.type == "table_row" and b.parent_id == one.id]
    assert [r.attributes["fields"]["c01"]["raw"] for r in rows] == ["0", "00027", "Undeclared"]
    assert len(raw["tables"]) == 2


def test_pdf_builder_change_invalidates_pdf_cache_but_preserves_office_cache(monkeypatch):
    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.parsers import pdf_structure
    from app.modules.knowledge.services.source_extraction import (
        EXTRACTION_VERSION,
        extraction_version_for,
    )

    pdf_version = extraction_version_for(".PDF")
    assert pdf_version != EXTRACTION_VERSION
    assert len(pdf_version) <= KnowledgeSourceRevision.__table__.c.normalizer_version.type.length
    monkeypatch.setattr(pdf_structure, "PDF_STRUCTURE_VERSION", pdf_structure.PDF_STRUCTURE_VERSION + "-next")
    assert extraction_version_for("pdf") != pdf_version
    assert extraction_version_for("docx") == EXTRACTION_VERSION
    assert extraction_version_for("xlsx") == EXTRACTION_VERSION
