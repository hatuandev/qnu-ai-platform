"""Relevance ordering survives prompt construction without losing source geometry."""

import json

from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.rag.answer.drafting import messages_for, sources_for


def hit(key, page, text):
    return SearchHit(
        chunk_id=key,
        document_id="document",
        version_id="version",
        publication_decision_id="publication",
        score=0.9,
        kind="paragraph",
        text=text,
        citations={f"ocr:{key}": {"page": page, "path": f"pages[{page - 1}].blocks[0]"}},
        structure={"context": {"parent": key}},
    )


def test_reranked_exception_is_not_buried_after_low_relevance_early_pages():
    hits = [
        hit("specific", 8, "A scoped exception with its own condition."),
        hit("general", 8, "General rule except the specified case."),
        hit("earlier", 1, "An unrelated early page."),
    ]
    result = SearchResponse(
        index_run_id="index", generation=1, status="results", hits=hits, eligible_documents=1
    )
    sources = sources_for(result)
    assert [s.chunk_id for s in sources] == [h.chunk_id for h in hits]
    assert [s.citations for s in sources] == [h.citations for h in hits]
    sent = json.loads(messages_for("Question", sources)[-1].content)
    assert sent["evidence"][0]["text"] == hits[0].text
    assert sources[0].evidence_id == "E1"
    assert result.hits == hits
