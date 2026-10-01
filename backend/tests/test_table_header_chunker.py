"""Unit Tests for Table Header Invariant & Contextual Injection Chunker."""

from __future__ import annotations

from app.modules.knowledge.chunker import (
    ClauseBasedChunker,
    SemanticChunker,
    count_cols,
    extract_table_header,
    generate_linearized_projections,
    is_likely_header_row,
    is_table_row,
    is_table_sep,
)


def test_table_syntax_and_header_recognition():
    """Verify table row detection and morphological header validation."""
    valid_hdr = "| STT | Lĩnh vực | Mã ngành | Giáo sư | Phó Giáo sư | Tiến sĩ | Thạc sĩ | Đại học | Tổng cộng |"
    valid_sep = "| :---: | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :---: |"
    data_row = "| 16.1 | Quản lý tài nguyên | 78501 | 0 | 3 | 18 | 10 | 0 | 31 |"
    hierarchical_row = "| 6.5.1 | Địa lí tự nhiên | 8440217 | 0 | 1 | 9 | 0 | 0 | 10 |"

    assert is_table_row(valid_hdr)
    assert is_table_sep(valid_sep)
    assert count_cols(valid_hdr) == 9

    assert is_likely_header_row(valid_hdr) is True
    assert is_likely_header_row(data_row) is False
    assert is_likely_header_row(hierarchical_row) is False

    schema = extract_table_header([valid_hdr, valid_sep, data_row])
    assert schema is not None
    assert schema.col_count == 9
    assert schema.column_names[0] == "STT"
    assert schema.column_names[3] == "Giáo sư"
    assert schema.column_names[8] == "Tổng cộng"


def test_semantic_chunker_headless_table_injection():
    """Verify SemanticChunker injects active table header into headless continuation chunks."""
    text = (
        "| STT | Tên ngành | Mã ngành | Điểm chuẩn |\n"
        "| :---: | :--- | :---: | :---: |\n"
        "| 1 | Công nghệ thông tin | 7480201 | 24.5 |\n"
        "| 2 | Kỹ thuật phần mềm | 7480103 | 23.0 |\n\n"
        "<!-- Trang 2 -->\n\n"
        "| 3 | Trí tuệ nhân tạo | 7480107 | 25.0 |\n"
        "| 4 | Khoa học dữ liệu | 7460108 | 24.0 |"
    )

    chunker = SemanticChunker(max_tokens=60, overlap_tokens=0)
    chunks = chunker.chunk(text)

    assert len(chunks) >= 2
    # Verify continuation chunk (containing row 3 and 4) has the header injected
    second_chunk = chunks[1]
    assert "| STT | Tên ngành | Mã ngành | Điểm chuẩn |" in second_chunk.content
    assert "| :---: | :--- | :---: | :---: |" in second_chunk.content
    assert "| 3 | Trí tuệ nhân tạo" in second_chunk.content
    assert second_chunk.metadata.get("has_table") is True
    assert second_chunk.metadata.get("table_cols") == 4
    assert second_chunk.metadata.get("table_columns") == ["STT", "Tên ngành", "Mã ngành", "Điểm chuẩn"]


def test_semantic_chunker_oversized_table_splitting():
    """Verify oversized tables are split cleanly across sub-chunks with header preserved in each."""
    header = "| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu |\n| :---: | :---: | :--- | :---: |"
    rows = [
        f"| {i} | 7480{i:03d} | Ngành đào tạo số {i} với nội dung chi tiết phong phú | {50 + i} |"
        for i in range(1, 40)
    ]
    table_text = header + "\n" + "\n".join(rows)

    chunker = SemanticChunker(max_tokens=150, overlap_tokens=0)
    chunks = chunker.chunk(table_text)

    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert "| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu |" in c.content, (
            f"Chunk {idx} is missing table header"
        )
        assert "| :---: | :---: | :--- | :---: |\n" in c.content, (
            f"Chunk {idx} is missing table separator"
        )
        assert c.token_count <= 200


def test_linearized_projections_for_summary_rows():
    """Verify unambiguous key-value projections are generated for summary/aggregate rows."""
    hdr_line = "| STT | Lĩnh vực | Mã ngành | Giáo sư. Tiến sĩ/ Giáo sư | Phó Giáo sư. Tiến sĩ | Tiến sĩ | Thạc sĩ | Đại học | Tổng cộng | Tổng quy đổi |"
    sep_line = "| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    schema = extract_table_header([hdr_line, sep_line])
    assert schema is not None

    total_row = "| | Tổng số giảng viên giảng dạy ĐH, CĐSP | | 2 | 85 | 383 | 356 | 5 | 831 | 788,2 |"
    projections = generate_linearized_projections(schema, [total_row])

    assert len(projections) == 1
    proj_text = projections[0]
    assert "> - [Tổng số giảng viên giảng dạy ĐH, CĐSP]:" in proj_text
    assert "Giáo sư. Tiến sĩ: 2" in proj_text
    assert "Phó Giáo sư. Tiến sĩ: 85" in proj_text
    assert "Tiến sĩ: 383" in proj_text
    assert "Thạc sĩ: 356" in proj_text
    assert "Đại học: 5" in proj_text
    assert "Tổng cộng: 831" in proj_text


def test_clause_based_chunker_table_preservation():
    """Verify ClauseBasedChunker preserves table header when article is subdivided."""
    header = "| STT | Đối tượng ưu tiên | Điểm cộng |\n| :---: | :--- | :---: |"
    rows = [
        f"| {i} | Đối tượng chính sách ưu tiên xét tuyển nhóm {i} theo quy định tuyển sinh hiện hành của nhà trường | {i * 0.5:.1f} |"
        for i in range(1, 35)
    ]
    content = (
        "Điều 12. Chính sách ưu tiên xét tuyển đối tượng và khu vực\n\n"
        + header
        + "\n"
        + "\n\n".join(rows)
    )

    chunker = ClauseBasedChunker()
    chunks = chunker.chunk(content)

    assert len(chunks) >= 2
    # Verify subsequent chunks retain table header
    for c in chunks:
        if any(r in c.content for r in rows[15:]):
            assert "| STT | Đối tượng ưu tiên | Điểm cộng |" in c.content
