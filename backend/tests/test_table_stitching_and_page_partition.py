"""Unit tests for multi-page table stitching, page partitioning, and layout preservation."""

from app.modules.knowledge.normalization.markdown_renderer import (
    render_canonical_document_markdown,
)
from app.modules.knowledge.normalization.models import (
    CanonicalBlock,
    CanonicalCell,
    CanonicalDocument,
    CanonicalRow,
    CanonicalTable,
    SourceSpan,
)
from app.modules.knowledge.normalization.table_reconstructor import (
    is_orphan_continuation_row,
    reconstruct_multi_page_tables,
)
from app.modules.knowledge.services.ingestion_service import ingestion_service


def test_is_orphan_continuation_row_protects_program_code():
    """Rows with a distinct 7-digit program code must NOT be treated as orphan continuation."""
    # Row with blank col 0 (group name) but has major code 7310608 in col 2
    row = CanonicalRow(
        row_id="r1",
        cells=[
            CanonicalCell(raw_value="", source_span=SourceSpan(page_number=14)),
            CanonicalCell(raw_value="Đông phương học", source_span=SourceSpan(page_number=14)),
            CanonicalCell(raw_value="7310608", source_span=SourceSpan(page_number=14)),
        ],
        source_pages=[14],
    )
    assert not is_orphan_continuation_row(row, key_col_idx=0)


def test_reconstruct_multi_page_tables_inherits_group_header():
    """Continuation page starting with an empty col 0 inherits the active group from previous page."""
    # Page 1 table ends with group "Tiếng Anh"
    t1 = CanonicalTable(
        table_id="t1",
        schema_key="mon_nganh_ma",
        headers=["Môn", "Ngành", "Mã"],
        rows=[
            CanonicalRow(
                row_id="r1",
                cells=[
                    CanonicalCell(raw_value="Tiếng Anh", source_span=SourceSpan(page_number=13)),
                    CanonicalCell(raw_value="Ngôn ngữ Anh", source_span=SourceSpan(page_number=13)),
                    CanonicalCell(raw_value="7220201", source_span=SourceSpan(page_number=13)),
                ],
                source_pages=[13],
            )
        ],
        source_pages=[13],
    )
    # Page 2 table begins with empty col 0 and code 7310608
    t2 = CanonicalTable(
        table_id="t2",
        schema_key="mon_nganh_ma",
        headers=["Môn", "Ngành", "Mã"],
        rows=[
            CanonicalRow(
                row_id="r2",
                cells=[
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=14)),
                    CanonicalCell(raw_value="Đông phương học", source_span=SourceSpan(page_number=14)),
                    CanonicalCell(raw_value="7310608", source_span=SourceSpan(page_number=14)),
                ],
                source_pages=[14],
            )
        ],
        source_pages=[14],
    )
    reconstructed = reconstruct_multi_page_tables([t1, t2])
    assert len(reconstructed) == 1
    master = reconstructed[0]
    assert len(master.rows) == 2
    assert master.rows[1].cells[0].raw_value == "Tiếng Anh"


def test_render_canonical_document_markdown_partitions_pages():
    """Multi-page tables render with headers across all their source pages."""
    table = CanonicalTable(
        table_id="master_t",
        schema_key="stt_tennganh",
        headers=["STT", "Tên ngành"],
        rows=[
            CanonicalRow(
                row_id="r1",
                cells=[
                    CanonicalCell(raw_value="1", source_span=SourceSpan(page_number=2)),
                    CanonicalCell(raw_value="Sư phạm Toán", source_span=SourceSpan(page_number=2)),
                ],
                source_pages=[2],
            ),
            CanonicalRow(
                row_id="r2",
                cells=[
                    CanonicalCell(raw_value="2", source_span=SourceSpan(page_number=3)),
                    CanonicalCell(raw_value="Sư phạm Tin", source_span=SourceSpan(page_number=3)),
                ],
                source_pages=[3],
            ),
        ],
        source_pages=[2, 3],
        bbox=(50.0, 400.0, 500.0, 600.0),
    )
    doc = CanonicalDocument(
        document_id="doc_test",
        page_count=3,
        blocks=[
            CanonicalBlock(
                block_id="b1",
                text="Phương thức tuyển sinh 2026",
                source_span=SourceSpan(page_number=2, bbox=(50.0, 100.0, 500.0, 200.0)),
            )
        ],
        tables=[table],
    )
    md = render_canonical_document_markdown(doc)
    assert "<!-- Page 2 -->" in md
    assert "<!-- Page 3 -->" in md
    p2_content = md.split("<!-- Page 2 -->")[1].split("<!-- Page 3 -->")[0]
    p3_content = md.split("<!-- Page 3 -->")[1]

    # Page 2 has text BEFORE table
    assert p2_content.find("Phương thức tuyển sinh 2026") < p2_content.find("| STT |")
    assert "| 1 | Sư phạm Toán |" in p2_content
    assert "| 2 | Sư phạm Tin |" not in p2_content

    # Page 3 has table header and row 2
    assert "| STT | Tên ngành |" in p3_content
    assert "| 2 | Sư phạm Tin |" in p3_content


def test_build_studio_pages_resolves_string_keys_and_page_set():
    """Studio page builder correctly reads string JSONB keys and includes all page_markdowns."""
    p_mds = {
        "1": "Page 1 intro",
        "2": "Page 2 content",
    }
    pages = ingestion_service.build_studio_pages(
        chunks=[],
        page_blocks={},
        document_id="doc_studio",
        page_markdowns=p_mds,
    )
    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert pages[0]["markdown_content"] == "Page 1 intro"
    assert pages[1]["page_number"] == 2
    assert pages[1]["markdown_content"] == "Page 2 content"


def test_synthesize_page_markdown_sorts_by_y():
    """Synthesizing markdown from blocks preserves vertical reading order."""
    blocks = [
        {
            "type": "table",
            "coordinates": {"x": 10.0, "y": 60.0, "width": 80.0, "height": 30.0},
            "text": "| A | B |\n|---|---|\n| 1 | 2 |",
        },
        {
            "type": "title",
            "coordinates": {"x": 10.0, "y": 10.0, "width": 80.0, "height": 10.0},
            "text": "TIÊU ĐỀ ĐẦU TRANG",
        },
    ]
    synth = ingestion_service._synthesize_page_markdown_from_blocks(blocks)
    assert synth.find("TIÊU ĐỀ ĐẦU TRANG") < synth.find("| A | B |")


def test_merge_split_roman_rows():
    """Split Roman numerals across rows (e.g. VII and I) are merged into one VIII row."""
    from app.modules.knowledge.normalization.table_reconstructor import _merge_split_roman_rows

    rows = [
        CanonicalRow(
            row_id="r1",
            cells=[
                CanonicalCell(raw_value="VII", source_span=SourceSpan(page_number=18)),
                CanonicalCell(raw_value="Công tác thi đua, khen thưởng", source_span=SourceSpan(page_number=18)),
                CanonicalCell(raw_value="", source_span=SourceSpan(page_number=18)),
            ],
            source_pages=[18],
        ),
        CanonicalRow(
            row_id="r2",
            cells=[
                CanonicalCell(raw_value="I", source_span=SourceSpan(page_number=18)),
                CanonicalCell(raw_value="", source_span=SourceSpan(page_number=18)),
                CanonicalCell(raw_value="", source_span=SourceSpan(page_number=18)),
            ],
            source_pages=[18],
        ),
        CanonicalRow(
            row_id="r3",
            cells=[
                CanonicalCell(raw_value="8.1", source_span=SourceSpan(page_number=18)),
                CanonicalCell(raw_value="Nhiệm vụ 8.1", source_span=SourceSpan(page_number=18)),
                CanonicalCell(raw_value="Phòng TC-NS", source_span=SourceSpan(page_number=18)),
            ],
            source_pages=[18],
        ),
    ]
    merged = _merge_split_roman_rows(rows)
    assert len(merged) == 2
    assert merged[0].cells[0].raw_value == "VIII"
    assert merged[0].cells[1].raw_value == "Công tác thi đua, khen thưởng"
    assert merged[1].cells[0].raw_value == "8.1"


def test_reconstruct_multi_page_tables_mixed_spacer_columns():
    """Continuation table with phantom spacer columns is normalized and stitched into master table without column drift."""
    from app.modules.knowledge.normalization.table_reconstructor import (
        reconstruct_multi_page_tables,
    )

    # Page 11: 7 clean columns
    t11 = CanonicalTable(
        table_id="t11",
        schema_key="schema_p11",
        headers=["TT", "Nội dung nhiệm vụ", "Đơn vị chủ trì", "Đơn vị phối hợp", "Thời gian bắt đầu", "Thời gian hoàn thành", "Sản phẩm kết quả"],
        rows=[
            CanonicalRow(
                row_id="r_4_10",
                cells=[
                    CanonicalCell(raw_value="4.10", source_span=SourceSpan(page_number=11)),
                    CanonicalCell(raw_value="Triển khai đề tài, đặc biệt là", source_span=SourceSpan(page_number=11)),
                    CanonicalCell(raw_value="Phòng KHCN&HTQT", source_span=SourceSpan(page_number=11)),
                    CanonicalCell(raw_value="PSU và các đơn vị liên quan", source_span=SourceSpan(page_number=11)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=11)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=11)),
                    CanonicalCell(raw_value="Báo cáo tiến độ", source_span=SourceSpan(page_number=11)),
                ],
                source_pages=[11],
            )
        ],
        source_pages=[11],
    )

    # Page 12: 11 columns with phantom None spacers, continuation row in index 3
    t12 = CanonicalTable(
        table_id="t12",
        schema_key="schema_p12",
        headers=["TT", "", "", "Nội dung nhiệm vụ", "", "Đơn vị chủ trì", "Đơn vị phối hợp", "Thời gian bắt đầu", "Thời gian hoàn thành", "Sản phẩm kết quả", ""],
        rows=[
            CanonicalRow(
                row_id="r_cont",
                cells=[
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="chương trình IUC-QNU giai đoạn 1.", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                    CanonicalCell(raw_value="", source_span=SourceSpan(page_number=12)),
                ],
                source_pages=[12],
            )
        ],
        source_pages=[12],
    )

    recon = reconstruct_multi_page_tables([t11, t12])
    assert len(recon) == 1
    master = recon[0]
    assert len(master.headers) == 7
    assert len(master.rows) == 1
    row_4_10 = master.rows[0]
    assert len(row_4_10.cells) == 7
    assert row_4_10.cells[0].raw_value == "4.10"
    # Column 1 (content) received the continuation text
    assert "Triển khai đề tài, đặc biệt là chương trình IUC-QNU giai đoạn 1." in row_4_10.cells[1].raw_value
    # Column 2 (lead) and Column 3 (coordination) remain intact and not overwritten
    assert row_4_10.cells[2].raw_value == "Phòng KHCN&HTQT"
    assert row_4_10.cells[3].raw_value == "PSU và các đơn vị liên quan"
    assert row_4_10.cells[6].raw_value == "Báo cáo tiến độ"


def test_classify_text_block_identifies_footer_page_number():
    """Standalone page numbers at top (header) or bottom (footer) are classified as footer."""
    from app.modules.knowledge.parsers.blocks import classify_text_block

    # Footer page number
    b_type, label = classify_text_block("2", top_percent=92.0, bottom_percent=94.0)
    assert b_type == "footer"
    assert label == "Số trang"

    b_type, label = classify_text_block("Trang 15/22", top_percent=90.0, bottom_percent=93.0)
    assert b_type == "footer"
    assert label == "Số trang"

    # Header page number (Nghị định 30/2020/NĐ-CP Điều 9 khoản 4)
    b_type, label = classify_text_block("3", top_percent=3.5, bottom_percent=5.0)
    assert b_type == "footer"
    assert label == "Số trang"


def test_clean_markdown_preserves_table_separators():
    """clean_markdown_text preserves standard Markdown table separator rows."""
    from app.modules.knowledge.cleaner import clean_markdown_text

    raw = (
        "| TT | Nội dung nhiệm vụ | Đơn vị chủ trì |\n"
        "| :---: | :--- | :--- |\n"
        "| 1.1 | Công tác đào tạo | Phòng Đào tạo |\n"
    )
    cleaned = clean_markdown_text(raw)
    assert "| :--- | :--- | :--- |" in cleaned
    assert "| 1.1 | Công tác đào tạo | Phòng Đào tạo |" in cleaned


def test_row_3_1_ban_hanh_not_matched_as_lead_unit():
    """Content starting with 'Ban hành' is not treated as a lead unit and columns align correctly."""
    from app.modules.knowledge.normalization.table_reconstructor import (
        _LEAD_UNIT_RE,
        _compact_task_row,
    )

    assert not _LEAD_UNIT_RE.match("Ban hành quy định đo lường")
    assert _LEAD_UNIT_RE.match("Phòng KT&BĐCL")

    # Construct row with spacer columns as PyMuPDF extracts for row 3.1
    row_3_1 = CanonicalRow(
        row_id="row_3_1",
        cells=[
            CanonicalCell(raw_value="3.1", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="", source_span=SourceSpan(page_number=7)),
            CanonicalCell(
                raw_value="Ban hành quy định đo lường, đánh giá CTĐT",
                source_span=SourceSpan(page_number=7),
            ),
            CanonicalCell(raw_value="", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="Phòng KT&BĐCL", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="Trung tâm S&HL", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="Các quy định đã ban hành", source_span=SourceSpan(page_number=7)),
            CanonicalCell(raw_value="", source_span=SourceSpan(page_number=7)),
        ],
        source_pages=[7],
    )
    semantic_indices = [0, 3, 5, 6, 7, 8, 9]
    compacted = _compact_task_row(row_3_1, 7, semantic_indices)
    assert compacted.cells[0].raw_value == "3.1"
    assert "Ban hành quy định đo lường" in compacted.cells[1].raw_value
    assert compacted.cells[2].raw_value == "Phòng KT&BĐCL"
    assert compacted.cells[3].raw_value == "Trung tâm S&HL"
    assert compacted.cells[6].raw_value == "Các quy định đã ban hành"



