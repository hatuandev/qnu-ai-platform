"""Lexical retrieval must compile to the expression the GIN index stores."""

from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from qnu.domains.knowledge.index import hybrid
from qnu.domains.knowledge.index.models import IndexChunk


class CapturingDb:
    statement = None

    async def execute(self, statement):
        CapturingDb.statement = statement
        return SimpleNamespace(all=list)


async def test_lexical_uses_literal_regconfig_for_expression_index():
    run = SimpleNamespace(id="idx_one", workspace_id="ws_one", collection_id="col_one")
    allowed = [SimpleNamespace(id="inp_one", version_id="ver_one")]
    assert await hybrid.lexical(CapturingDb(), run, allowed, "Chỉ tiêu", 5) == []
    sql = str(CapturingDb.statement.compile(dialect=postgresql.dialect()))
    assert "to_tsvector('simple'::regconfig, kb_index_chunks.text)" in sql
    assert "websearch_to_tsquery('simple'::regconfig" in sql


def test_model_declares_the_gin_expression_index():
    index = next(i for i in IndexChunk.__table__.indexes if i.name == "ix_kb_index_chunks_fts")
    assert index.dialect_options["postgresql"]["using"] == "gin"
    assert "to_tsvector('simple'::regconfig, text)" in str(index.expressions[0])
