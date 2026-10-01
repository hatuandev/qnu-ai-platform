"""Unit tests for Vietnamese Stopwords Manager & Dynamic Domain Suppression."""

from app.core.stopwords import (
    extract_collection_domain_stopwords,
    get_vietnamese_stopwords,
    is_stopword,
    reload_stopwords,
)
from app.modules.rag.retriever import extract_weighted_tokens, select_ilike_tokens


def test_get_vietnamese_stopwords_loads_valid_dictionary():
    """Verify stopwords are loaded from file, non-empty, and free of comments/empty strings."""
    stopwords = get_vietnamese_stopwords()

    assert isinstance(stopwords, frozenset)
    assert len(stopwords) >= 40

    # Must contain essential grammatical and domain stopwords
    assert "và" in stopwords
    assert "của" in stopwords
    assert "trong" in stopwords
    assert "được" in stopwords
    assert "trường" in stopwords
    assert "đại" in stopwords
    assert "học" in stopwords
    assert "đhqn" in stopwords

    # No comment lines or empty tokens
    assert all(not w.startswith("#") for w in stopwords)
    assert all(len(w.strip()) > 0 for w in stopwords)


def test_reload_stopwords_clears_cache():
    """Verify reload_stopwords operates properly and returns frozenset."""
    initial = get_vietnamese_stopwords()
    reloaded = reload_stopwords()
    assert reloaded == initial
    assert isinstance(reloaded, frozenset)


def test_extract_collection_domain_stopwords():
    """Verify dynamic extraction of collection-name tokens as domain stopwords."""
    col_name = "Thông tin tuyển sinh Đại học Quy Nhơn"
    domain_stops = extract_collection_domain_stopwords(col_name)

    assert "thông" in domain_stops
    assert "tin" in domain_stops
    assert "tuyển" in domain_stops
    assert "sinh" in domain_stops
    assert "đại" in domain_stops
    assert "học" in domain_stops
    assert "quy" in domain_stops
    assert "nhơn" in domain_stops

    # Empty or None should return empty set safely
    assert extract_collection_domain_stopwords(None) == set()
    assert extract_collection_domain_stopwords("") == set()


def test_is_stopword_with_extra_suppression():
    """Verify is_stopword checks base dictionary and optional extra set."""
    assert is_stopword("và") is True
    assert is_stopword("của") is True
    assert is_stopword("toán") is False

    # Extra domain suppression
    assert is_stopword("toán", extra_stopwords={"toán"}) is True


def test_extract_weighted_tokens_with_dynamic_stopwords():
    """Verify extract_weighted_tokens integrates base and dynamic domain stopwords."""
    query = "Học phí ngành CNTT năm 2026"
    tokens = dict(extract_weighted_tokens(query))

    # 'cntt' (acronym: 2.5) and '2026' (code: 3.5) must be present
    assert "cntt" in tokens
    assert "2026" in tokens
    # 'học' and 'ngành' are in base stopwords
    assert "học" not in tokens
    assert "ngành" not in tokens

    # Dynamic suppression: if 'cntt' is passed as extra_stopwords, it should be excluded
    tokens_suppressed = dict(extract_weighted_tokens(query, extra_stopwords={"cntt"}))
    assert "cntt" not in tokens_suppressed
    assert "2026" in tokens_suppressed


def test_select_ilike_tokens_uses_dynamic_stopwords():
    """Verify select_ilike_tokens respects extra domain stopwords."""
    query = "Tổ hợp xét tuyển X06 X07 X25 môn Toán"
    ilike_tokens = select_ilike_tokens(query, extra_stopwords={"toán"})

    assert "x06" in ilike_tokens
    assert "x07" in ilike_tokens
    assert "x25" in ilike_tokens
    # 'toán' was dynamically suppressed
    assert "toán" not in ilike_tokens
