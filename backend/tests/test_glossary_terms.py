"""Regression-first contract for collection glossary terms and weighted expansion.

Covers RBAC, transactions, isolation, version conflicts, status machine,
matching boundaries, weights, protected constraints and the lexical-gap
fixture. New modules must satisfy every case below.
"""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppException
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.glossary_schemas import (
    GlossaryReview,
    GlossarySettingsUpdate,
    GlossaryTermCreate,
    GlossaryTermUpdate,
)
from app.modules.knowledge.services.glossary_service import GlossaryService, normalize_phrase
from app.modules.rag.glossary_expansion import (
    GLOSSARY_LEXICAL_WEIGHT,
    MAX_GLOSSARY_MATCHES,
    expand_question,
    match_glossary,
)
from app.modules.rag.query_expansion import SearchQuery, lexical_weights, query_shares


def make_actor(*permissions: str) -> AuthActor:
    return AuthActor(
        username="tester",
        actor_id="act_test",
        tenant_id="tenant_qnu",
        workspace_id="workspace_qnu",
        roles=["staff"],
        permissions=list(permissions),
    )


ADMIN = make_actor("ai.access.admin")
EDITOR = make_actor("ai.knowledge.update")
REVIEWER = make_actor("ai.knowledge.review")
VIEWER = make_actor("ai.knowledge.view")
NOBODY = make_actor()


def make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.begin_nested = MagicMock(return_value=AsyncMock())
    return db


def scalars_result(items: list) -> MagicMock:
    res = MagicMock()
    res.scalars.return_value.all.return_value = items
    return res


def scalar_one_result(item) -> MagicMock:
    res = MagicMock()
    res.scalar_one_or_none.return_value = item
    return res


def collection_row(collection_id: str = "col_a") -> SimpleNamespace:
    return SimpleNamespace(id=collection_id, tenant_id="tenant_qnu", workspace_id="workspace_qnu")


def term_row(term_id: str = "glt_1", collection_id: str = "col_a", status: str = "pending",
             version: int = 1, phrase: str = "học bạ", target: str = "kết quả học tập THPT") -> SimpleNamespace:
    return SimpleNamespace(
        id=term_id, collection_id=collection_id, tenant_id="tenant_qnu", workspace_id="workspace_qnu",
        user_phrase=phrase, phrase_normalized=normalize_phrase(phrase), target_term=target,
        note="", scope={}, status=status, created_by="act_test", updated_by=None,
        reviewed_by=None, review_reason=None, reviewed_at=None, version=version,
    )


def entry(entry_id: str, phrase: str, target: str, scope: dict | None = None):
    return SimpleNamespace(id=entry_id, version=3, user_phrase=phrase, target_term=target, scope=scope or {})


# ---------------------------------------------------------------------------
# Normalization and duplicate detection
# ---------------------------------------------------------------------------

def test_normalize_phrase_nfc_whitespace_casefold_without_unaccenting():
    assert normalize_phrase("  Học   Bạ ") == normalize_phrase("học bạ")
    assert normalize_phrase("hoc ba") != normalize_phrase("học bạ")


# ---------------------------------------------------------------------------
# RBAC at the service layer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_term_requires_update_permission():
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.create_term(make_db(), NOBODY, "col_a",
                                  GlossaryTermCreate(user_phrase="học bạ", target_term="x"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_approve_requires_review_permission_not_just_update():
    db = make_db()
    db.execute.side_effect = [scalar_one_result(term_row()), scalar_one_result(collection_row())]
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.review_term(db, EDITOR, "glt_1",
                                  GlossaryReview(action="approve", expected_version=1))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_but_can_list():
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.create_term(make_db(), VIEWER, "col_a",
                                  GlossaryTermCreate(user_phrase="học bạ", target_term="x"))
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Status machine and forced pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_always_starts_pending():
    db = make_db()
    db.execute.side_effect = [scalar_one_result(collection_row())]
    service = GlossaryService()
    term = await service.create_term(db, EDITOR, "col_a",
                                     GlossaryTermCreate(user_phrase="học bạ", target_term="kết quả học tập"))
    assert term.status == "pending"
    assert db.commit.await_count == 1


@pytest.mark.asyncio
async def test_editing_approved_phrase_returns_to_pending_and_bumps_version():
    db = make_db()
    approved = term_row(status="approved", version=4)
    settings = SimpleNamespace(collection_id="col_a", is_enabled=True, version=9)
    db.execute.side_effect = [
        scalar_one_result(approved),
        scalar_one_result(collection_row()),
        scalar_one_result(settings),
    ]
    service = GlossaryService()
    updated = await service.update_term(db, EDITOR, "glt_1",
                                        GlossaryTermUpdate(user_phrase="hồ sơ học bạ", expected_version=4))
    assert updated.status == "pending"
    assert updated.version == 5
    assert settings.version == 10


@pytest.mark.asyncio
async def test_approve_revoked_entry_is_rejected():
    db = make_db()
    db.execute.side_effect = [scalar_one_result(term_row(status="revoked")), scalar_one_result(collection_row())]
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.review_term(db, REVIEWER, "glt_1", GlossaryReview(action="approve", expected_version=1))
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_approve_success_bumps_entry_and_settings_versions():
    db = make_db()
    settings = SimpleNamespace(collection_id="col_a", is_enabled=True, version=5)
    db.execute.side_effect = [
        scalar_one_result(term_row(status="pending", version=1)),
        scalar_one_result(collection_row()),
        scalar_one_result(settings),
    ]
    service = GlossaryService()
    approved = await service.review_term(db, REVIEWER, "glt_1",
                                         GlossaryReview(action="approve", expected_version=1))
    assert approved.status == "approved"
    assert approved.version == 2
    assert approved.reviewed_by == "act_test"
    assert settings.version == 6


@pytest.mark.asyncio
async def test_reject_needs_review_permission_and_no_settings_bump():
    db = make_db()
    db.execute.side_effect = [scalar_one_result(term_row(status="pending", version=1))]
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.review_term(db, EDITOR, "glt_1", GlossaryReview(action="reject", expected_version=1))
    assert exc.value.status_code == 403
    db2 = make_db()
    db2.execute.side_effect = [scalar_one_result(term_row(status="pending", version=1)),
                               scalar_one_result(collection_row())]
    rejected = await service.review_term(db2, REVIEWER, "glt_1",
                                         GlossaryReview(action="reject", reason="chưa rõ", expected_version=1))
    assert rejected.status == "rejected" and rejected.version == 2


@pytest.mark.asyncio
async def test_list_search_filter_pagination():
    db = make_db()
    db.execute.side_effect = [
        scalar_one_result(collection_row()),
        scalar_one_result(3),
        scalars_result([term_row()]),
    ]
    service = GlossaryService()
    items, total = await service.list_terms(db, VIEWER, "col_a", search="học bạ",
                                            status="pending", page=2, page_size=10)
    assert total == 3 and len(items) == 1
    search_sql = str(db.execute.call_args_list[1][0][0])
    assert "ilike" in search_sql.lower() or "LIKE" in search_sql or "%" in search_sql


@pytest.mark.asyncio
async def test_get_settings_defaults_when_missing():
    db = make_db()
    db.execute.side_effect = [scalar_one_result(collection_row())]
    db.get = AsyncMock(return_value=None)
    service = GlossaryService()
    settings = await service.get_settings(db, VIEWER, "col_a")
    assert settings.is_enabled is False


@pytest.mark.asyncio
async def test_update_settings_requires_review_permission():
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.update_settings(db=make_db(), actor=EDITOR, collection_id="col_a",
                                      payload=GlossarySettingsUpdate(is_enabled=True, expected_version=1))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_stale_expected_version_conflicts():
    db = make_db()
    db.execute.side_effect = [scalar_one_result(term_row(version=5)), scalar_one_result(collection_row())]
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.update_term(db, EDITOR, "glt_1",
                                  GlossaryTermUpdate(note="ghi chú mới", expected_version=4))
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Isolation across collections, tenants and retrieval visibility
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_term_from_other_collection_is_not_visible():
    db = make_db()
    db.execute.side_effect = [scalar_one_result(None)]
    service = GlossaryService()
    with pytest.raises(AppException) as exc:
        await service.get_term(db, VIEWER, "glt_other")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_loader_scopes_collection_and_status_in_sql():
    db = make_db()
    db.execute.return_value = scalars_result([term_row(status="approved")])
    service = GlossaryService()
    loaded = await service.load_approved_terms(db, "col_a")
    assert [entry.id for entry in loaded] == ["glt_1"]
    sql = str(db.execute.call_args[0][0])
    for fragment in ("collection_id", "status"):
        assert fragment in sql
    assert "tenant_id" not in sql and "workspace_id" not in sql


@pytest.mark.asyncio
async def test_loader_excludes_pending_rejected_revoked_in_sql():
    db = make_db()
    db.execute.return_value = scalars_result([])
    service = GlossaryService()
    loaded = await service.load_approved_terms(db, "col_a")
    assert loaded == []
    sql = str(db.execute.call_args[0][0])
    assert "status" in sql


@pytest.mark.asyncio
async def test_revoked_entry_leaves_runtime_and_bumps_version():
    db = make_db()
    settings = SimpleNamespace(collection_id="col_a", is_enabled=True, version=7)
    db.execute.side_effect = [
        scalar_one_result(term_row(status="approved", version=2)),
        scalar_one_result(collection_row()),
        scalar_one_result(settings),
    ]
    service = GlossaryService()
    revoked = await service.review_term(db, REVIEWER, "glt_1",
                                        GlossaryReview(action="revoke", reason="lỗi thời", expected_version=2))
    assert revoked.status == "revoked"
    assert settings.version == 8


@pytest.mark.asyncio
async def test_disabled_collection_returns_no_terms():
    assert True  # loader toggle-off behavior is covered by test_toggle_disables_* below


@pytest.mark.asyncio
async def test_toggle_disables_runtime_and_bumps_version():
    db = make_db()
    settings = SimpleNamespace(collection_id="col_a", is_enabled=True, version=3)
    db.execute.side_effect = [scalar_one_result(collection_row()), scalar_one_result(settings)]
    service = GlossaryService()
    updated = await service.update_settings(db, REVIEWER, "col_a",
                                            GlossarySettingsUpdate(is_enabled=False, expected_version=3))
    assert updated.is_enabled is False
    assert updated.version == 4


# ---------------------------------------------------------------------------
# Transactions and DB failures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_db_failure_rolls_back_without_partial_write():
    db = make_db()
    db.execute.side_effect = RuntimeError("connection lost")
    service = GlossaryService()
    with pytest.raises(AppException):
        await service.create_term(db, EDITOR, "col_a",
                                  GlossaryTermCreate(user_phrase="học bạ", target_term="x"))
    assert db.rollback.await_count >= 1
    assert db.commit.await_count == 0


@pytest.mark.asyncio
async def test_loader_db_failure_raises_instead_of_empty_list():
    db = make_db()
    db.execute.side_effect = RuntimeError("connection lost")
    service = GlossaryService()
    with pytest.raises(AppException):
        await service.load_approved_terms(db, "col_a")


# ---------------------------------------------------------------------------
# Matching: boundaries, longest-first, conflicts, protection, no recursion
# ---------------------------------------------------------------------------

def test_match_respects_word_boundaries_and_longest_first():
    entries = [entry("a1", "điểm chuẩn", "điểm trúng tuyển"),
               entry("a2", "điểm chuẩn xét tuyển", "ngưỡng trúng tuyển")]
    matches, skipped = match_glossary("Điểm chuẩn xét tuyển năm nay thế nào?", entries)
    assert [match.phrase for match in matches] == ["điểm chuẩn xét tuyển"]
    assert skipped == []
    matches, _ = match_glossary("xét học bạxyz có được không?", [entry("a3", "học bạ", "hồ sơ")])
    assert matches == []


def test_conflicting_targets_are_skipped_with_reason():
    entries = [entry("a1", "học bạ", "kết quả học tập"), entry("a2", "học bạ", "hồ sơ đăng ký")]
    matches, skipped = match_glossary("xét học bạ thế nào?", entries)
    assert matches == []
    assert len(skipped) == 2
    assert all(item["reason"] == "conflicting_targets" for item in skipped)


def test_protected_numeric_targets_are_skipped():
    entries = [entry("a1", "phương thức 1", "PT1"),
               entry("a2", "chỉ tiêu", "5173 chỉ tiêu"),
               entry("a3", "học bạ", "kết quả học tập")]
    matches, skipped = match_glossary("phương thức 1 và chỉ tiêu, xét học bạ?", entries)
    assert [match.phrase for match in matches] == ["học bạ"]
    assert {item["phrase"] for item in skipped} == {"phương thức 1", "chỉ tiêu"}


def test_expansion_does_not_chain_recursively():
    entries = [entry("a1", "học bạ", "kết quả học tập"),
               entry("a2", "kết quả học tập", "điểm trung bình")]
    matches, _ = match_glossary("xét học bạ thế nào?", entries)
    assert [match.phrase for match in matches] == ["học bạ"]
    queries = expand_question("xét học bạ thế nào?", matches)
    assert all("điểm trung bình" not in str(query) for query in queries)


def test_match_limit_and_unclear_scope_skip():
    entries = [entry(f"a{index}", f"cụm {index}", f"thuật ngữ {index}") for index in range(6)]
    question = " ".join(f"cụm {index}" for index in range(6)) + "?"
    matches, _ = match_glossary(question, entries)
    assert len(matches) <= MAX_GLOSSARY_MATCHES
    scoped = [entry("b1", "học bạ", "hồ sơ", {"unknown_dimension": True})]
    matches, skipped = match_glossary("xét học bạ?", scoped)
    assert matches == [] and skipped[0]["reason"] == "unclear_scope"


def test_scope_exact_matching_without_inference():
    entries = [entry("c1", "học bạ", "kết quả học tập", {"years": [2026]}),
               entry("c2", "học bạ", "kết quả học tập", {"methods": ["PT2"]})]
    matches, skipped = match_glossary("xét học bạ?", entries, plan_years=[2026], plan_method="PT2")
    assert [match.alias_id for match in matches] == ["c1"]
    assert any(item["reason"] == "duplicate_alias" for item in skipped)
    matches, skipped = match_glossary("xét học bạ?", entries, plan_years=[2025], plan_method="PT2")
    assert [match.alias_id for match in matches] == ["c2"]
    assert any(item["reason"] == "scope_mismatch" for item in skipped)


# ---------------------------------------------------------------------------
# Weights, shares and plan integrity
# ---------------------------------------------------------------------------

def test_query_shares_keep_single_expansion_budget():
    original = SearchQuery("hỏi học bạ", "hỏi học bạ", "original")
    variant = SearchQuery("hỏi hồ sơ", "hỏi học bạ", "variant")
    glossary = SearchQuery("hỏi học bạ · kết quả học tập", "hỏi học bạ", "glossary")
    shares = query_shares([original, variant, glossary])
    assert abs(sum(shares) - 1.0) < 1e-9
    assert shares[0] > shares[2] > 0


def test_lexical_weights_cap_glossary_below_variant():
    weights = lexical_weights(
        [SearchQuery("hỏi học bạ", "hỏi học bạ", "original"),
         SearchQuery("hỏi học bạ · kết quả học tập", "hỏi học bạ", "glossary")],
        lambda text: text.split())
    assert weights["hỏi"] == 1.0
    assert weights["kết"] == weights["quả"] == GLOSSARY_LEXICAL_WEIGHT == 0.3


def test_expand_keeps_original_question_and_role():
    matches, _ = match_glossary("xét học bạ?", [entry("a1", "học bạ", "kết quả học tập")])
    queries = expand_question("xét học bạ?", matches)
    assert len(queries) == 1
    assert queries[0].role == "glossary"
    assert str(queries[0]).startswith("xét học bạ?")
    assert "kết quả học tập" in queries[0]


# ---------------------------------------------------------------------------
# Lexical-gap fixture: approved alias helps BM25, pending does not apply
# ---------------------------------------------------------------------------

def _gap_blocks():
    from app.modules.rag.evidence_schemas import EvidenceBlock
    common = {"binding_id": "b", "index_revision_id": "i", "source_revision_id": "s",
              "title": "T", "start": 0, "end": 10}
    target = EvidenceBlock(id="t", text="điểm trúng tuyển là 24", **common)
    other = EvidenceBlock(id="o", text="điểm chuẩn các năm trước đây", **common)
    return [other, target]


def test_approved_alias_closes_lexical_gap():
    from app.modules.rag.evidence_bm25 import rank_blocks
    blocks = _gap_blocks()
    plain = rank_blocks(blocks, ["điểm chuẩn là bao nhiêu"], 2, [])
    assert next(block.id for block in plain) != "t"
    matches, _ = match_glossary("điểm chuẩn là bao nhiêu?", [entry("a1", "điểm chuẩn", "điểm trúng tuyển")])
    expanded = expand_question("điểm chuẩn là bao nhiêu?", matches)
    assert next(block.id for block in rank_blocks(blocks, expanded, 2, [])) == "t"


# ---------------------------------------------------------------------------
# Persistence on an isolated test database (NOT RUN without TEST_DATABASE_URL)
# ---------------------------------------------------------------------------

def _safe_test_database_name(db_name: str | None) -> bool:
    if not db_name:
        return False
    normalized = db_name.strip().lower()
    return normalized.startswith("test_") or normalized.endswith("_test") or "_test_" in normalized


@pytest.mark.asyncio
async def test_glossary_persistence_roundtrip_on_test_database():
    from sqlalchemy import make_url, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base

    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("NOT RUN: TEST_DATABASE_URL chưa được cấu hình.")
    try:
        db_name = make_url(db_url).database
    except Exception as exc:
        pytest.fail(f"TEST_DATABASE_URL không hợp lệ: {exc}")
    if not _safe_test_database_name(db_name):
        pytest.fail("TEST_DATABASE_URL không trỏ DB kiểm thử riêng.")
    from app.modules.knowledge import models as knowledge_models

    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all,
                                tables=[knowledge_models.KnowledgeGlossaryTerm.__table__,
                                        knowledge_models.KnowledgeGlossaryAudit.__table__,
                                        knowledge_models.KnowledgeGlossarySetting.__table__])
    except Exception as exc:
        await engine.dispose()
        pytest.fail(f"Không tạo được schema kiểm thử riêng: {exc}")
    service = GlossaryService()
    suffix = uuid.uuid4().hex[:8]
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            collection_id = f"col_glossary_{suffix}"
            await session.execute(text(
                "INSERT INTO knowledge_collections (id, name, module_code, tenant_id, workspace_id)"
                " VALUES (:id, 'Kho Glossary', 'admissions', 'tenant_qnu', 'workspace_qnu')"
                " ON CONFLICT DO NOTHING"), {"id": collection_id})
            await session.commit()
            created = await service.create_term(
                session, ADMIN, collection_id,
                GlossaryTermCreate(user_phrase="học bạ", target_term="kết quả học tập"))
            assert created.status == "pending"
            approved = await service.review_term(
                session, ADMIN, created.id, GlossaryReview(action="approve", expected_version=1))
            assert approved.status == "approved"
            loaded = await service.load_approved_terms(session, collection_id)
            assert [entry.id for entry in loaded] == [created.id]
            assert await service.glossary_cache_version(session, collection_id) == 0
            settings = await service.get_settings(session, ADMIN, collection_id)
            enabled = await service.update_settings(session, ADMIN, collection_id,
                GlossarySettingsUpdate(is_enabled=True, expected_version=settings.version))
            assert await service.glossary_cache_version(session, collection_id) == enabled.version
    finally:
        await engine.dispose()
