"""Regression checks for glossary scope, transaction and stale ORM boundaries."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.modules.knowledge.glossary_schemas import GlossaryTermCreate, GlossaryTermUpdate
from app.modules.knowledge.models import KnowledgeGlossarySetting, KnowledgeGlossaryTerm
from app.modules.knowledge.services.glossary_service import (
    GlossaryService,
    _check_version,
    _get_settings_locked,
)
from app.modules.rag.glossary_expansion import match_glossary, resolve_glossary_queries


def alias(target="kết quả học tập", scope=None):
    return SimpleNamespace(id="alias", version=1, user_phrase="học bạ",
                           target_term=target, scope={} if scope is None else scope)


@pytest.mark.parametrize("scope", [
    {"years": ["2026"]}, {"years": [True]}, {"years": [2026.5]},
    {"years": ["không phải năm"]}, {"years": 2026}, {"years": [0]},
    {"methods": "PT2"}, {"entities": [""]}, {"unknown": True},
])
def test_invalid_scope_rejected_on_create_and_update(scope):
    with pytest.raises(ValidationError):
        GlossaryTermCreate(user_phrase="học bạ", target_term="kết quả học tập", scope=scope)
    with pytest.raises(ValidationError):
        GlossaryTermUpdate(expected_version=1, scope=scope)


@pytest.mark.parametrize("scope", [{"years": ["bad"]}, {"methods": 5}, [2026], [], False, 0])
def test_invalid_legacy_scope_is_skipped_not_a_chat_error(scope):
    matches, skipped = match_glossary("học bạ năm 2026?", [alias(scope=scope)], plan_years=[2026])
    assert not matches
    assert skipped[0]["reason"] == "invalid_scope"


def test_distinct_year_targets_resolve_scope_before_conflicts():
    entries = [alias("hồ sơ đăng ký", {"years": [2025]}),
               alias("kết quả học tập", {"years": [2026]})]
    matches, skipped = match_glossary("học bạ năm 2026?", entries, plan_years=[2026])
    assert [match.term for match in matches] == ["kết quả học tập"]
    assert [item["reason"] for item in skipped] == ["scope_mismatch"]
    assert not match_glossary("học bạ năm 2025 và 2026?", entries,
                              plan_years=[2025, 2026])[0]


def test_fact_branch_uses_literal_method_and_entity_without_model_call():
    entries = [alias(scope={"methods": ["PT2"], "entities": ["Ngành A"]})]
    assert match_glossary("PT2 học bạ Ngành A?", entries)[0]
    assert not match_glossary("PT20 học bạ Ngành AB?", entries)[0]
    assert not match_glossary("học bạ?", entries)[0]
    assert not match_glossary("PT2 học bạ Ngành A?", entries, plan_method="PT1")[0]


def db_mock():
    db = AsyncMock()
    context = AsyncMock()
    db.begin_nested = MagicMock(return_value=context)
    return db, context


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["glossary_cache_version", "load_approved_terms"])
async def test_missing_table_is_isolated_by_savepoint(method):
    db, context = db_mock()
    cause = RuntimeError("undefined table")
    cause.sqlstate = "42P01"
    db.execute.side_effect = ProgrammingError("select", {}, cause)
    result = await getattr(GlossaryService(), method)(db, "col_a")
    assert result == (0 if method == "glossary_cache_version" else [])
    db.begin_nested.assert_called_once()
    assert context.__aexit__.await_args.args[0] is ProgrammingError
    db.rollback.assert_not_awaited()  # Parent work must survive the failed read.


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["glossary_cache_version", "load_approved_terms"])
async def test_other_programming_errors_are_not_hidden_as_disabled(method):
    db, _ = db_mock()
    cause = RuntimeError("permission denied")
    cause.sqlstate = "42501"
    db.execute.side_effect = ProgrammingError("select", {}, cause)
    with pytest.raises(AppException) as exc:
        await getattr(GlossaryService(), method)(db, "col_a")
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_resolver_requires_only_collection_and_question():
    db, _ = db_mock()
    service = "app.modules.knowledge.services.glossary_service.glossary_service"
    with patch(f"{service}.glossary_cache_version", new=AsyncMock(return_value=2)), \
         patch(f"{service}.load_approved_terms", new=AsyncMock(return_value=[alias()])):
        queries, trace = await resolve_glossary_queries(db, "col_a", "học bạ?")
    assert queries and trace["enabled"]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", [KnowledgeGlossaryTerm, KnowledgeGlossarySetting])
async def test_lock_refreshes_identity_map_before_checking_expected_version(model):
    # A real SQLAlchemy identity map, not a mock returning a pre-selected row.
    # SQLite proves the refresh semantics; PostgreSQL row-lock scheduling is
    # separately gated by TEST_DATABASE_URL, never the application database.
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("knowledge_collections", metadata, sa.Column("id", sa.String, primary_key=True))
    table = model.__table__.to_metadata(metadata)
    if model is KnowledgeGlossaryTerm:
        table.c.scope.type = sa.JSON()
    metadata.create_all(engine)
    values = {"collection_id": "col_a", "version": 1}
    if model is KnowledgeGlossaryTerm:
        values.update(id="term", user_phrase="học bạ", phrase_normalized="học bạ",
                      target_term="kết quả học tập", scope={})
    with engine.begin() as connection:
        connection.execute(table.insert().values(**values))
    try:
        with Session(engine, autoflush=False) as session:
            key = "term" if model is KnowledgeGlossaryTerm else "col_a"
            stale = session.get(model, key)
            with engine.begin() as connection:
                connection.execute(table.update().values(version=2))
            assert stale.version == 1
            db = AsyncMock()
            db.execute.side_effect = lambda stmt: session.execute(stmt)
            if model is KnowledgeGlossarySetting:
                locked = await _get_settings_locked(db, "col_a")
            else:
                with patch("app.modules.knowledge.services.glossary_service.get_scoped_collection",
                           new=AsyncMock(return_value=SimpleNamespace(id="col_a"))):
                    locked, _ = await GlossaryService()._load_term_for_update(db, None, key)
            assert locked is stale and locked.version == 2
            with pytest.raises(AppException) as exc:
                _check_version(locked.version, 1)
            assert exc.value.status_code == 409
    finally:
        engine.dispose()
