"""Clean-source normalization must never certify or destroy uncertain evidence."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.normalization.clean_content import (
    attach_content_integrity,
    inspect_content,
    normalize_content,
)
from app.modules.knowledge.services.source_artifact import (
    build_source_artifact,
    get_structured_review_state,
)
from app.modules.knowledge.services.source_ingestion_service import (
    compute_sha256,
    source_ingestion_service,
)
from app.modules.knowledge.services.source_pages import (
    canonical_pages,
    merge_edited_manifest,
    normalize_source_pages,
    validate_edit_pages,
)


@pytest.mark.parametrize("source", [
    "# Heading\n\n0\n2025\n777\n\n[^a]: Footnote 2024",
    "| Key | Value |\n| --- | --- |\n| A | 0 | extra |\n| B | |",
    "- first\n  - nested\n    continuation\n\n1. numbered\n\ntext  \nnext",
    "```python\n  amount = 24.125\n```\n\n~~~\n# Not a heading\n~~~",
    "$$\nx  =  1\n2\n$$\n\n\\[\nx = 3\n\\]",
    "    a  =  1\n    b  =  2",
    "    long indented code block ending with an identifier\nnext prose",
    "![source](local:image.png)\n\nA\ufffd\x00B",
])
def test_protected_structure_values_and_uncertainty_survive(source):
    assert normalize_content(source) == source
    assert normalize_content(normalize_content(source)) == normalize_content(source)
    stored, _ = normalize_source_pages(source, 1, [{"page_number": 1, "extracted_text": source}])
    assert canonical_pages(stored)[0]["markdown_content"] == source


def test_reflow_only_soft_prose_not_paragraphs_or_numbers():
    line = "Một đoạn văn bản dài đủ để xác định đây là dòng văn xuôi"
    result = normalize_content(line + "\nđược xuống dòng do bố cục.\n\nĐoạn khác.\n2026")
    assert result == line + " được xuống dòng do bố cục.\n\nĐoạn khác.\n2026"
    assert inspect_content(result, line + "\nđược xuống dòng do bố cục.\n\nĐoạn khác.\n2026")["changes"] == {}


def test_original_page_text_and_blocks_survive_normalization_and_edit():
    raw = "# Tài liệu\n\n0\n\n| A | B |\n| --- | --- |\n| x | 1 | EXTRA |"
    block = {"id": "original", "text": raw, "coordinates": {"left": 1}}
    _, manifest = normalize_source_pages(raw, 2, [{"page_number": 2, "extracted_text": raw, "blocks": [block]}])
    _, edited = normalize_source_pages("<!-- Trang 2 -->\nĐã sửa 2", 2)
    merged = merge_edited_manifest(manifest, edited)
    assert merged[0]["extracted_markdown"] == raw
    assert merged[0]["blocks"] == [block]
    assert merged[0]["layout_text_alignment"] == "stale"
    assert merged[0]["normalization"]["output_hash"] == compute_sha256("Đã sửa 2")
    assert "extracted_markdown" not in merge_edited_manifest([{"page": 2}], edited)[0]


def test_repeated_margins_flagged_not_deleted():
    pages = [{"page_number": p, "extracted_text": f"Cơ quan\n\nNội dung {p}\n\nCuối trang"} for p in (1, 2)]
    md, manifest = normalize_source_pages("", 2, pages)
    assert md.count("Cơ quan") == md.count("Cuối trang") == 2
    assert manifest[0]["margin_candidates"] == ["Cơ quan", "Cuối trang"]


@pytest.mark.parametrize("before,after,code", [
    ("24,125 năm 2025", "24,13 năm 2026", "CONTENT_NUMBERS_CHANGED"),
    ("Không áp dụng.", "Áp dụng.", "CONTENT_NEGATIONS_CHANGED"),
    ("83 triệu đồng khi đủ điều kiện", "83 đồng", "CONTENT_WORDING_CHANGED"),
    ("| A | B |\n| --- | --- |\n| 1 | 2 |", "| A | B |\n| --- | --- |", "CONTENT_TABLE_ROWS_REDUCED"),
    ("$$x = 1$$", "x 1", "CONTENT_FORMULAS_REDUCED"),
    ("[^a]: condition", "condition", "CONTENT_FOOTNOTES_REDUCED"),
])
def test_edit_integrity_warns_without_rewriting(before, after, code):
    report = inspect_content(after, before)
    assert code in {i["code"] for i in report["issues"]}
    assert report["requires_review"]
    assert report["semantic_correctness"] == "not_measured"
    assert report["content_hash"] == compute_sha256(after)
    finding = next(i for i in report["issues"] if i["code"] == code)
    assert finding["page_number"] is None and finding["line_number"] is None


def test_table_missing_cells_formula_and_note_locations():
    report = inspect_content("<!-- Trang 3 -->\n| A | B |\n| --- | --- |\n| x |\n\n$$\nx = 1\n[^a]", page_count=3)
    issue = next(i for i in report["issues"] if i["code"] == "CONTENT_TABLE_WIDTH")
    assert (issue["page_number"], issue["line_number"]) == (3, 4)
    assert {"CONTENT_FORMULA_REVIEW", "CONTENT_FOOTNOTE_REVIEW"} <= {i["code"] for i in report["issues"]}


def test_empty_column_does_not_become_zero_and_edited_revision_needs_review():
    md = "| Name | Amount |\n| --- | --- |\n| A | |\n| B | |"
    artifact = build_source_artifact(md, 0, {})
    attach_content_integrity(artifact, md, 0, md)
    assert artifact["tables"][0]["rows"][0][1] == ""
    assert any(i["code"] == "CONTENT_EMPTY_COLUMN" for i in artifact["issues"])
    rev = SimpleNamespace(parse_provenance={"structured_artifact": artifact}, canonical_hash=compute_sha256(md))
    assert get_structured_review_state(rev)[1]


def result(value):
    response = MagicMock()
    response.scalar_one_or_none.return_value = value
    response.scalars.return_value.first.return_value = value
    return response


@pytest.mark.asyncio
async def test_edit_creates_audited_draft_keeps_serving_and_source_immutable():
    binding = KnowledgeBinding(id="bnd_clean", collection_id="col", status="active", active_source_revision_id="old")
    raw = "<!-- Trang 1 -->\nKhông dùng điểm 25.5"
    rev = KnowledgeSourceRevision(id="old", binding_id=binding.id, revision_no=1, origin_file_hash="binaryhash",
        canonical_markdown=raw, canonical_hash=compute_sha256(raw), status="ready",
        page_manifest=[{"page": 1, "extracted_markdown": "Không dùng điểm 25.5"}])
    db = AsyncMock(); db.add = MagicMock()
    db.execute.side_effect = [result(rev), result(1)]
    with patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=binding)), \
         patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()), \
         patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()):
        saved = await source_ingestion_service.update_revision_content(db, "col", binding.id, rev.id,
            "<!-- Trang 1 -->\nDùng điểm 26.5", actor_id="editor", change_reason="Đối chiếu bản gốc", expected_canonical_hash=rev.canonical_hash)
    assert saved.status == "review_required" and saved.id != rev.id
    assert binding.active_source_revision_id == "old" and rev.canonical_markdown == raw
    assert saved.origin_file_hash == rev.origin_file_hash
    assert saved.page_manifest[0]["extracted_markdown"] == "Không dùng điểm 25.5"
    assert saved.parse_provenance["content_review"]["actor_id"] == "editor"
    assert saved.parse_provenance["content_review"]["base_revision_id"] == rev.id
    assert get_structured_review_state(saved)[1]
    with pytest.raises(AppException, match="Cần người duyệt"):
        source_ingestion_service._apply_review_decision(binding, saved, saved.parse_provenance["structured_artifact"], "approved", None, "reviewer")
    assert binding.active_source_revision_id == "old"
    source_ingestion_service._apply_review_decision(binding, saved, saved.parse_provenance["structured_artifact"], "approved", "Đã đối chiếu và xác nhận thay đổi số/phủ định", "reviewer")
    assert saved.status == "ready" and binding.active_source_revision_id == saved.id


@pytest.mark.asyncio
async def test_preview_is_revision_bound_and_read_only():
    binding = KnowledgeBinding(id="bnd", collection_id="col")
    rev = KnowledgeSourceRevision(id="rev", binding_id="bnd", canonical_markdown="# Title", canonical_hash="hash", page_manifest=[])
    db = AsyncMock(); db.execute.return_value = result(rev)
    with patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=binding)):
        preview = await source_ingestion_service.preview_clean_content(db, "col", "bnd", "rev", "# Title", "hash")
        assert preview["revision_id"] == "rev"
        db.commit.assert_not_awaited()
        with pytest.raises(AppException) as error:
            await source_ingestion_service.preview_clean_content(db, "col", "bnd", "rev", "# Title", "stale")
        assert error.value.status_code == 409
        db.execute.return_value = result(None)
        with pytest.raises(AppException) as error:
            await source_ingestion_service.preview_clean_content(db, "col", "bnd", "foreign", "text")
        assert error.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("actor,reason,expected,code", [
    (None, "reason", "hash", "CONTENT_REVIEW_REASON_REQUIRED"),
    ("actor", " ", "hash", "CONTENT_REVIEW_REASON_REQUIRED"),
    ("actor", "reason", "stale", "SOURCE_CONTENT_CHANGED"),
])
async def test_edit_rejects_missing_audit_and_stale_base(actor, reason, expected, code):
    binding = KnowledgeBinding(id="bnd", collection_id="col")
    rev = KnowledgeSourceRevision(id="rev", binding_id="bnd", canonical_hash="hash")
    db = AsyncMock(); db.execute.return_value = result(rev)
    with patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=binding)), \
         patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()), \
         patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()), \
         pytest.raises(AppException) as error:
        await source_ingestion_service.update_revision_content(db, "col", "bnd", "rev", "text",
            actor_id=actor, change_reason=reason, expected_canonical_hash=expected)
    assert error.value.code == code
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("markdown,manifest", [
    ("<!-- Trang 9 -->text", [{"page": None}]),
    ("<!-- Trang 2 -->text", [{"page": 1}, {"page": 2}]),
    ("<!-- Trang 2 -->A\n<!-- Trang 1 -->B", [{"page": 1}, {"page": 2}]),
    ("text", [{"page": 1}, {"page": 2}]),
])
def test_edit_cannot_forge_page_provenance(markdown, manifest):
    with pytest.raises(AppException) as error:
        validate_edit_pages(markdown, manifest)
    assert error.value.code == "SOURCE_PAGE_BOUNDARIES_CHANGED"


def test_unknown_page_raw_extraction_survives_edit_without_claiming_page_one():
    original = [{"page": None, "extracted_markdown": "raw unknown"}]
    _, draft = normalize_source_pages("edited", 0)
    assert merge_edited_manifest(original, draft)[0]["extracted_markdown"] == "raw unknown"


@pytest.mark.asyncio
async def test_studio_never_calls_current_markdown_raw_extraction():
    for raw in (None, "original text"):
        manifest = [{"page": None}]
        if raw is not None:
            manifest[0]["extracted_markdown"] = raw
        rev = KnowledgeSourceRevision(id="rev", binding_id="bnd", canonical_markdown="current cleaned", page_manifest=manifest)
        binding = KnowledgeBinding(id="bnd", collection_id="col", active_source_revision=rev)
        with patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=binding)):
            response = await source_ingestion_service.get_source_studio_data(AsyncMock(), "col", "bnd")
        assert response.pages[0].raw_text == (raw or "")
        assert response.pages[0].raw_text_available == (raw is not None)
        assert not response.pagination_known and response.pages[0].image_url is None


@pytest.mark.asyncio
async def test_http_preview_permission_and_edit_actor_are_server_owned():
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.main import app
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor

    actor = AuthActor(actor_id="trusted", username="reviewer", role="officer", roles=["officer"], permissions=["ai.knowledge.update"])
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_actor] = lambda: actor
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    url = "/platform/v1alpha1/knowledge/collections/col/sources/bnd/revisions/rev"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch.object(source_ingestion_service, "preview_clean_content", AsyncMock(return_value={
                "revision_id": "rev", "base_hash": "hash", "canonical_markdown": "text", "report": {},
            })) as preview:
                response = await client.post(url + "/clean-preview", json={"canonical_markdown": "text"})
                assert response.status_code == 200
                assert preview.await_args.args[1:4] == ("col", "bnd", "rev")
                actor.permissions = []
                response = await client.post(url + "/clean-preview", json={"canonical_markdown": "text"})
                assert response.status_code == 403 and preview.await_count == 1
                actor.permissions = ["ai.knowledge.update"]
            with patch.object(source_ingestion_service, "update_revision_content", AsyncMock(side_effect=AppException("test", code="EXPECTED_TEST", status_code=409))) as update:
                response = await client.patch(url + "/content", json={"canonical_markdown": "text", "actor_id": "forged", "change_reason": "Reviewed"})
                assert response.status_code == 409
                assert update.await_args.kwargs["actor_id"] == "trusted"
                assert update.await_args.kwargs["change_reason"] == "Reviewed"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
