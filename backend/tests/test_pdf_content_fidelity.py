"""Source-backed PDF reconciliation must preserve literals and fail closed on real loss."""

import copy
import hashlib

import pymupdf
import pytest

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.parsers.pdf_evidence import capture_native_page
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document
from app.modules.knowledge.services.automatic_ingestion import evaluate_content

storage, database = lifecycle.storage, lifecycle.database


def test_table_engine_lost_glyph_is_blocking_instead_of_a_source_unknown(monkeypatch):
    from app.modules.knowledge.parsers import pdf_evidence

    original_finder = pdf_evidence.find_page_tables

    def finder(page):
        result = original_finder(page)
        for detected in result.tables:
            matrix = detected.extract()
            matrix[1][1] = (
                "9"  # Real page contains 0; never accept a different digit as literal coverage.
            )
            detected.extract = lambda *args, m=matrix, **kwargs: copy.deepcopy(m)
        return result

    monkeypatch.setattr(pdf_evidence, "find_page_tables", finder)
    with pymupdf.open() as pdf:
        table(pdf.new_page())
        _, _, doc = build(pdf)
    container = next(b for b in doc.blocks if b.type == "table")
    assert any(
        f.code == "native_cell_glyph_conflict" and f.status == "unresolved"
        for f in container.quality_flags
    )
    conflict = container.source_data["table"]["raw_native"]["cell_text_conflicts"][0]
    assert conflict["original"] == "9" and conflict["projected"] == "0"


def evidence(pdf):
    raw = pdf.tobytes()
    return raw, {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "pages": [
            {"page": p.number + 1, "native": capture_native_page(p), "engine_used": "native"}
            for p in pdf
        ],
    }


def build(pdf, mutate=None):
    raw, source = evidence(pdf)
    if mutate:
        mutate(source)
    return (
        raw,
        source,
        build_pdf_document(source, filename="test.pdf", sha256=hashlib.sha256(raw).hexdigest()),
    )


def table(page, *, header=True, group=False, top=50, bottom=170, orphan=False):
    xs, ys = [40, 180, 320], [top, top + 30, top + 60, top + 90, bottom]
    band = (0.85, 0.9, 0.95)
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    for x in xs:
        if group and x == 180:
            page.draw_line((x, top), (x, top + 30))
            page.draw_line((x, top + 60), (x, bottom))
        else:
            page.draw_line((x, top), (x, bottom))
    rows = [
        ["Ref", "Value"] if header else ["Alpha", "North"],
        ["Band shared by subsequent rows"] if group else ["002", "0"],
        ["003", "5"],
        ["004", "8"],
    ]
    if orphan:
        rows[1] = ["", "remaining text"]
    for ri, row in enumerate(rows):
        bold = header and (ri == 0 or group and ri == 1)
        if bold:
            page.draw_rect((40, ys[ri], 320, ys[ri + 1]), color=None, fill=band, overlay=False)
        for ci, value in enumerate(row):
            page.insert_text(
                (50 + ci * 140, ys[ri] + 19), value, fontname="hebo" if bold else "helv", fontsize=9
            )


def test_full_width_group_after_header_is_not_a_second_header():
    with pymupdf.open() as pdf:
        table(pdf.new_page(), group=True)
        _, _, doc = build(pdf)
    container = next(b for b in doc.blocks if b.type == "table")
    assert [c["header_path"] for c in container.attributes["columns"]] == [["Ref"], ["Value"]]
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert len(rows) == 3
    assert rows[0].body == "Band shared by subsequent rows"
    assert rows[0].attributes["interpretation"] == "literal_only"
    assert all(f["state"] == "ambiguous" for f in rows[0].attributes["fields"].values())


def test_verified_headerless_grid_is_literal_only_and_never_becomes_facts():
    with pymupdf.open() as pdf:
        table(pdf.new_page(), header=False)
        _, _, doc = build(pdf)
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert rows[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert rows[0].attributes["fields"]["c02"]["raw"] == "North"
    assert len(rows) == 4 and all(r.attributes["interpretation"] == "literal_only" for r in rows)
    _, artifact = project_document(doc, {"sha256": "a" * 64, "structured_sha256": "b" * 64}, {})
    assert artifact["facts"] == []
    assert evaluate_content(artifact, {})["status"] == "READY_WITH_LIMITATIONS"


@pytest.mark.parametrize("visible", [True, False])
def test_only_visible_native_glyphs_override_conflicting_ocr(visible):
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=400, height=400)
        page.insert_text((40, 80), "Payment 12000", render_mode=0 if visible else 3)

        def add_ocr(source):
            source["pages"][0].update(
                ocr_selected=True,
                raw_ocr_available=True,
                engine_used="test-ocr",
                ocr_dimensions={"width": 400, "height": 400},
                ocr_raw_page={
                    "blocks": [
                        {"type": "text", "text": "Payment 72000", "block_bbox": [35, 65, 180, 85]}
                    ]
                },
            )

        _, _, doc = build(pdf, add_ocr)
    text = [b for b in doc.blocks if b.type in {"text", "section"}]
    if visible:
        assert any("12000" in b.body for b in text)
        assert not any("72000" in b.body for b in text)
        assert not any(f.code == "native_ocr_conflict" for b in text for f in b.quality_flags)
        assert any(b.source_data.get("alternatives") for b in text)
    else:
        assert any(f.code == "native_ocr_conflict" for b in text for f in b.quality_flags)


def test_code_background_is_not_a_figure_but_unrelated_artwork_remains():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for i, line in enumerate(["def evaluate(record):", "    return record['value'] >= 0"]):
            page.draw_rect((40, 50 + 15 * i, 400, 65 + 15 * i), color=None, fill=(0.94, 0.95, 0.96))
            page.insert_text((45, 61 + 15 * i), line, fontname="cour", fontsize=9)
        page.draw_rect((50, 150, 150, 210), fill=(0.2, 0.4, 0.8))
        _, _, doc = build(pdf)
    assert len([b for b in doc.blocks if b.type == "figure"]) == 1
    code = next(b for b in doc.blocks if b.type == "code")
    assert "def evaluate(record):" in code.body and "record['value'] >= 0" in code.body


def test_value_label_inside_a_solid_bar_does_not_make_it_decorative_code_background():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.draw_rect((40, 50, 400, 65), color=None, fill=(0.4, 0.5, 0.6))
        page.insert_text((45, 61), "120", fontname="cour", fontsize=9)
        _, _, doc = build(pdf)
    assert len([b for b in doc.blocks if b.type == "figure"]) == 1


@pytest.mark.parametrize("identifier", ["source_key", "001_02", "2027_02", "am_k2"])
def test_glyph_baselines_restore_reordered_identifier_without_rewriting_raw_matrix(
    monkeypatch, identifier
):
    from app.modules.knowledge.parsers import pdf_evidence

    original_finder = pdf_evidence.find_page_tables

    def finder(page):
        result = original_finder(page)
        for detected in result.tables:
            matrix = detected.extract()
            # Reproduce Table.extract separating low underscore glyphs from the baseline.
            matrix[1][0] = identifier.replace("_", " ") + "\n" + "_" * identifier.count("_")
            detected.extract = lambda *args, m=matrix, **kwargs: copy.deepcopy(m)
        return result

    monkeypatch.setattr(pdf_evidence, "find_page_tables", finder)
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for y in [50, 80, 110, 140, 170]:
            page.draw_line((40, y), (320, y))
        for x in [40, 180, 320]:
            page.draw_line((x, 50), (x, 170))
        for ri, row in enumerate([["Ref", "Value"], [identifier, "0"], ["ABC", "5"], ["XYZ", "8"]]):
            for ci, text in enumerate(row):
                page.insert_text((50 + ci * 140, 70 + ri * 30), text, fontsize=9)
        raw, _, doc = build(pdf)
    container = next(b for b in doc.blocks if b.type == "table")
    source = container.source_data["table"]["raw_native"]
    assert source["matrix"][1][0] != identifier
    assert source["glyph_matrix"][1][0] == identifier
    assert source["cell_text_projections"][0]["glyphs"]
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert rows[1].attributes["fields"]["c01"]["raw"] == identifier
    assert raw.startswith(b"%PDF")


@pytest.mark.parametrize("change", ["text", "missing", "extra", "geometry", "source"])
def test_pdf_source_verifier_rejects_changed_or_missing_canonical_evidence(change):
    from app.modules.knowledge.parsers.pdf_fidelity import verify_pdf_source

    with pymupdf.open() as pdf:
        table(pdf.new_page())
        raw, source, doc = build(pdf)
    verify_pdf_source(doc, raw, source)
    altered = doc.model_copy(deep=True)
    if change == "text":
        altered.blocks[-1].attributes["fields"]["c02"]["raw"] = "999"
    elif change == "missing":
        altered.blocks.pop()
    elif change == "extra":
        altered.blocks.append(altered.blocks[-1].model_copy(update={"id": "extra"}))
    elif change == "geometry":
        altered.blocks[-1].attributes["field_sources"]["c01"]["bbox"][0] += 10
    else:
        source = {**source, "source_sha256": "f" * 64}
    with pytest.raises(ValueError):
        verify_pdf_source(altered, raw, source)


def test_replayed_raw_native_proposal_cannot_forge_a_header_role():
    from app.modules.knowledge.parsers.pdf_fidelity import verify_pdf_source

    with pymupdf.open() as pdf:
        table(pdf.new_page(), header=False)
        raw, source = evidence(pdf)
    source = copy.deepcopy(source)
    source["pages"][0]["native"]["tables"][0]["header_evidence"] = {
        "status": "verified",
        "depth": 1,
    }
    forged = build_pdf_document(source, filename="test.pdf", sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):
        verify_pdf_source(forged, raw, source)


@pytest.mark.parametrize("intervening", [False, True])
def test_continuations_need_matching_headers_and_no_new_caption(intervening):
    with pymupdf.open() as pdf:
        table(pdf.new_page(width=400, height=230), top=100, bottom=220)
        page = pdf.new_page(width=400, height=230)
        if intervening:
            page.insert_text((40, 15), "Separate table")
        table(page, top=25, bottom=145)
        _, _, doc = build(pdf)
    tables = [b for b in doc.blocks if b.type == "table"]
    assert bool(tables[1].attributes.get("continuation")) is not intervening
    assert len(tables) == 2  # No source row is silently merged/dropped.


def test_small_bottom_note_is_preserved_without_assigning_a_table_scope():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text(
            (50, 100), "Ordinary body establishes the dominant font size.", fontsize=12
        )
        page.insert_text((50, 740), "Preserve this note literally.", fontsize=8)
        _, _, doc = build(pdf)
    note = next(b for b in doc.blocks if b.type == "note")
    assert "Preserve this note" in note.body and not note.context_refs
    assert all(f.status == "confirmed" for f in note.quality_flags)


def test_page_break_fragment_preserves_two_cells_and_dependency_without_filling_identity():
    with pymupdf.open() as pdf:
        table(pdf.new_page(width=400, height=230), top=100, bottom=220)
        table(pdf.new_page(width=400, height=230), top=25, bottom=145, orphan=True)
        _, _, doc = build(pdf)
    fragment = next(b for b in doc.blocks if b.attributes.get("row_role") == "source_row_fragment")
    origin = next(
        b for b in doc.blocks if b.id == fragment.attributes["continuation_of"]["block_id"]
    )
    assert fragment.attributes["fields"]["c01"]["raw"] == ""
    assert fragment.attributes["fields"]["c02"]["raw"] == "remaining text"
    assert fragment.id in origin.context_refs
    assert fragment.attributes["fields"]["c02"]["state"] == "ambiguous"


@pytest.mark.parametrize("separator", [True, False])
def test_numbered_bottom_paragraph_requires_separator_to_be_a_native_footnote(separator):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        if separator:
            page.draw_line((50, 730), (220, 730))
        page.insert_text((50, 745), "2")
        page.insert_text((70, 745), "Literal note without a uniquely marked anchor.")
        _, _, doc = build(pdf)
    notes = [b for b in doc.blocks if b.attributes.get("footnote_marker")]
    assert bool(notes) is separator
    if separator:
        assert notes[0].attributes["scope_status"] == "unassigned" and not notes[0].context_refs


def test_pdf_image_needs_its_own_authenticated_transcription_not_an_ocr_label():
    from io import BytesIO

    from PIL import Image

    from app.modules.knowledge.parsers.pdf_fidelity import verify_pdf_source
    from app.modules.knowledge.services import source_figure_review as service

    image = BytesIO()
    Image.new("RGB", (30, 20), "#385060").save(image, format="PNG")
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_image((50, 100, 200, 200), stream=image.getvalue())
        raw, source, doc = build(pdf)
    block = next(b for b in doc.blocks if b.type == "figure")
    assert any(f.code == "visual_content_untranscribed" for f in block.quality_flags)
    text = "Confirmed TEST content only"
    receipt = {
        "version": service.VERSION,
        "origin_sha256": hashlib.sha256(raw).hexdigest(),
        "binding_id": "test-binding",
        "image_sha256": block.attributes["resource"]["sha256"],
        "transcription": text,
        "transcription_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "approval_kind": "explicit_user_confirmation",
        "approval_reference": "TEST confirmation",
        "recorded_by": "test-actor",
        "publication_granted": False,
    }
    service.apply_figure_reviews(doc, raw, [receipt], "test-binding")
    service.verify_figure_reviews(doc, raw, [receipt], "test-binding")
    verify_pdf_source(doc, raw, source)
    assert block.body == text and not block.quality_flags and not block.context_refs
    with pytest.raises(AppException, match="server"):
        service.verify_figure_reviews(doc, raw, [], "test-binding")


@pytest.mark.parametrize("change", ["sidecar_hash", "sidecar_missing", "forged_native"])
async def test_indexing_verifier_rejects_broken_pdf_source_evidence(database, change):
    import json

    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.services.automatic_ingestion import verify_content_source
    from app.modules.knowledge.services.qnu_docx_artifacts import build_qnu_markdown_artifact
    from app.modules.knowledge.services.qnu_serving import prepare_standard_revision
    from app.modules.knowledge.services.source_extraction import SourceExtraction

    with pymupdf.open() as pdf:
        table(pdf.new_page())
        raw, source, doc = build(pdf)
    async with database.factory() as db:
        rev = await db.get(KnowledgeSourceRevision, database.ids[2])
        rev.origin_file_hash = hashlib.sha256(raw).hexdigest()
        await database.storage.save(rev.snapshot_storage_path, raw)
        ref = await build_qnu_markdown_artifact(
            extraction=SourceExtraction(
                raw_text="", page_count=1, qnu_document=doc, pdf_evidence=source
            ),
            document_id=rev.binding_id,
            revision_id=rev.id,
            title=None,
            snapshot_path=rev.snapshot_storage_path,
        )
        rev.snapshot_metadata, rev.parse_provenance, rev.quality_report = (
            {"qnu_markdown": ref},
            {},
            {"overall_status": "passed"},
        )
        await prepare_standard_revision(rev, automatic=True)
        target = rev.snapshot_metadata["qnu_markdown"]["raw_evidence"]
        if change == "sidecar_hash":
            target["sha256"] = "f" * 64
        elif change == "sidecar_missing":
            target["path"] = "nonexistent-evidence.json"
        else:
            source["pages"][0]["native"]["tables"][0]["matrix"][1][1] = "999"
            fake = json.dumps(source).encode()
            await database.storage.save("forged-test-evidence.json", fake)
            target.update(path="forged-test-evidence.json", sha256=hashlib.sha256(fake).hexdigest())
        with pytest.raises(AppException) as caught:
            await verify_content_source(rev)
        assert caught.value.code == "SOURCE_LAYOUT_MISMATCH"
