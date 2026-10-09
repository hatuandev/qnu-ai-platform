from pathlib import Path

path = Path("tests/test_rag.py")
content = path.read_text(encoding="utf-8")

old = '''def test_fit_dim_pads_and_truncates():
    """Model vectors must be fitted exactly to the Qdrant dimension."""
    from app.modules.rag.vector_indexer import VectorIndexer

    indexer = VectorIndexer()
    assert len(indexer._fit_dim([0.5] * 2048)) == indexer.vector_size
    assert len(indexer._fit_dim([0.5] * 10)) == indexer.vector_size'''

new = '''def test_fit_dim_strict_dimension_invariant():
    """Model vectors must match exactly the Qdrant dimension. Truncation or padding is strictly rejected."""
    import pytest
    from app.core.exceptions import AppException
    from app.modules.rag.vector_indexer import VectorIndexer

    indexer = VectorIndexer()
    assert len(indexer._fit_dim([0.5] * indexer.vector_size)) == indexer.vector_size

    with pytest.raises(AppException) as exc_info:
        indexer._fit_dim([0.5] * (indexer.vector_size + 100))
    assert exc_info.value.code == "VECTOR_DIMENSION_MISMATCH"

    with pytest.raises(AppException) as exc_info:
        indexer._fit_dim([0.5] * 10)
    assert exc_info.value.code == "VECTOR_DIMENSION_MISMATCH"'''

old_crlf = old.replace('\n', '\r\n')
new_crlf = new.replace('\n', '\r\n')

if old_crlf in content:
    content = content.replace(old_crlf, new_crlf)
    path.write_text(content, encoding="utf-8")
    print("REPLACED CRLF")
elif old in content:
    content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")
    print("REPLACED LF")
else:
    print("NOT FOUND")
