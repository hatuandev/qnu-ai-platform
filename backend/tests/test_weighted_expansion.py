"""Expansion must improve matching without duplicate votes or invented scope."""

import pytest

from app.modules.rag.evidence_bm25 import lexical_weights, rank_blocks, tokens
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.evidence_search import search_queries
from app.modules.rag.query_expansion import SearchQuery, query_shares
from app.modules.rag.retriever import extract_weighted_tokens
from tests.test_enumeration_and_followup import block


def test_plain_bm25_api_keeps_original_term_weights():
    assert lexical_weights(["alpha beta"], tokens) == dict.fromkeys(tokens("alpha beta"), 1.0)


def test_expansion_mass_is_bounded_and_duplicate_original_terms_never_stack():
    original = "Alpha 2026"
    expanded = SearchQuery(original + " " + " ".join(f"term{i}" for i in range(100)), original, "variant")
    weights = lexical_weights([expanded, expanded], tokens)
    originals = set(tokens(original))
    assert all(weights[term] == 1 for term in originals)
    assert sum(weight for term, weight in weights.items() if term not in originals) <= len(originals) * .35 / .65 + 1e-8


def test_group_budget_preserves_authority_even_with_feedback_first():
    queries = [SearchQuery("focus", "original", "feedback"), SearchQuery("original", "original", "original"),
               SearchQuery("variant", "original", "variant")]
    shares = query_shares(queries)
    assert shares[1] == .65 and sum(shares) == pytest.approx(1)
    assert sum(shares[index] for index in (0, 2)) == pytest.approx(.35)
    duplicated = [*queries, SearchQuery(" VARIANT ", "original", "variant")]
    assert query_shares(duplicated) == [*shares, 0]


def test_repeated_original_text_is_not_a_new_vote():
    queries = [SearchQuery("alpha", "alpha", "original"), SearchQuery("alpha", "alpha", "variant")]
    assert query_shares(queries) == [1, 0]


def test_feedback_and_variants_cannot_add_numbers_or_relabel_authority():
    plan = QueryPlan(query="Alpha 2026", search_queries=["Alpha 2037", "Alfa 2026"], years=[2026])
    queries = search_queries("Alpha 2026", plan, ["need context", "2099"])
    assert queries[0].role == "feedback"
    assert any(query.role == "original" for query in queries)
    assert all("2037" not in query and "2099" not in query for query in queries)
    assert sum(query_shares(queries)) == pytest.approx(1)


def test_weighted_matching_finds_document_only_matching_the_expanded_terminology():
    query = SearchQuery("entry threshold", "admission floor", "variant")
    candidates = [block("entry threshold", 1), block("unrelated content", 2)]
    assert rank_blocks(candidates, [query], 2)[0].id == candidates[0].id


def test_sql_morphological_weights_discount_new_terms_only_for_tagged_queries():
    original = "Alpha"
    expanded = SearchQuery("Alpha AdditionalWord", original, "variant")
    weighted = dict(extract_weighted_tokens(expanded))
    baseline = dict(extract_weighted_tokens(str(expanded)))
    assert weighted["alpha"] == baseline["alpha"]
    assert weighted["additionalword"] < baseline["additionalword"]
