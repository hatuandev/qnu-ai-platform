"""Unit tests for Domain Record Normalization, Quality Gate & Record-Aware Chunking."""

from __future__ import annotations

from app.modules.knowledge.chunker import (
    AdmissionsRecordChunker,
    get_chunker,
)
from app.modules.knowledge.facts import fact_extractor
from app.modules.knowledge.normalization.models import (
    CanonicalCell,
    CanonicalDocument,
    CanonicalRow,
    CanonicalTable,
    SourceSpan,
)
from app.modules.knowledge.normalization.quality_gate import DataQualityGate
from app.modules.knowledge.normalization.record_normalizer import (
    AdmissionProgramRecord,
    AdmissionsRecordNormalizer,
    ImplementationPlanRecordNormalizer,
    ImplementationTaskRecord,
)
from app.modules.knowledge.normalization.text_normalizer import (
    is_administrative_heading,
    join_wrapped_paragraph_lines,
    normalize_encoding,
    normalize_whitespace,
)
from app.modules.knowledge.parsers.base import ParsedContent
from app.modules.knowledge.services.ingestion_service import IngestionService


def _cell(val: str, page: int = 1) -> CanonicalCell:
    return CanonicalCell(
        raw_value=val,
        normalized_value=val if val else None,
        source_span=SourceSpan(page_number=page),
    )


def test_text_normalizer_encoding_and_whitespace():
    raw_text = "Trường  Đại học   Quy Nhơn \ufeff \x00\n\n\n\nKhoa CNTT   "
    clean = normalize_whitespace(normalize_encoding(raw_text))
    assert "\ufeff" not in clean
    assert "\x00" not in clean
    assert clean == "Trường Đại học Quy Nhơn\n\nKhoa CNTT"


def test_join_wrapped_paragraph_lines():
    lines = [
        "Trường Đại học Quy Nhơn thông báo",
        "tuyển sinh trình độ đại học chính quy",
        "năm học 2026 - 2027.",
        "Mọi chi tiết xin liên hệ phòng đào tạo.",
    ]
    reflowed = join_wrapped_paragraph_lines(lines)
    assert len(reflowed) == 2
    assert reflowed[0] == "Trường Đại học Quy Nhơn thông báo tuyển sinh trình độ đại học chính quy năm học 2026 - 2027."
    assert reflowed[1] == "Mọi chi tiết xin liên hệ phòng đào tạo."


def test_is_administrative_heading():
    assert is_administrative_heading("I. MỤC ĐÍCH, YÊU CẦU") is True
    assert is_administrative_heading("Điều 1. Phạm vi điều chỉnh") is True
    assert is_administrative_heading("KẾ HOẠCH TRIỂN KHAI NHIỆM VỤ") is True
    assert is_administrative_heading("Đây là một đoạn văn bản bình thường không phải tiêu đề.") is False


def test_admissions_record_normalizer_extracts_programs():
    tbl = CanonicalTable(
        table_id="tbl_ts",
        schema_key="key_ts",
        headers=["STT", "Mã ngành", "Tên ngành", "Phương thức", "Chỉ tiêu", "Tổ hợp môn"],
        rows=[
            CanonicalRow(
                row_id="r1",
                cells=[
                    _cell("1"),
                    _cell("7140114"),
                    _cell("Quản lý giáo dục"),
                    _cell("1, 2, 4"),
                    _cell("50"),
                    _cell("(Văn, Sử, Địa)\n(Văn, Toán, Anh)"),
                ],
                source_pages=[2],
            )
        ],
        source_pages=[2],
    )
    doc = CanonicalDocument(
        document_id="doc_tuyensinh",
        tables=[tbl],
        metadata={"title": "Thông báo thông tin tuyển sinh 2026"},
    )

    normalizer = AdmissionsRecordNormalizer()
    assert normalizer.supports(doc) is True

    records = normalizer.normalize(doc)
    assert len(records) == 1
    prog = records[0]
    assert isinstance(prog, AdmissionProgramRecord)
    assert prog.program_code == "7140114"
    assert prog.program_name == "Quản lý giáo dục"
    assert prog.admission_methods == ["1", "2", "4"]
    assert prog.expected_quota == 50
    assert len(prog.subject_combinations) == 2
    assert prog.subject_combinations[0] == ["Văn", "Sử", "Địa"]
    assert prog.subject_combinations[1] == ["Văn", "Toán", "Anh"]


def test_implementation_plan_normalizer_extracts_tasks():
    tbl = CanonicalTable(
        table_id="tbl_kh",
        schema_key="key_kh",
        headers=["TT", "Nội dung nhiệm vụ", "Đơn vị chủ trì", "Đơn vị phối hợp", "Thời gian bắt đầu", "Thời gian hoàn thành", "Sản phẩm kết quả"],
        rows=[
            # Category group header
            CanonicalRow(
                row_id="cat1",
                cells=[_cell("I"), _cell("Công tác phát triển đội ngũ, tổ chức, nhân sự"), _cell(""), _cell(""), _cell(""), _cell(""), _cell("")],
                source_pages=[3],
            ),
            # Task row
            CanonicalRow(
                row_id="task1",
                cells=[
                    _cell("1.1"),
                    _cell("Triển khai công tác quy hoạch Ban Chấp hành"),
                    _cell("Văn phòng"),
                    _cell("Đảng ủy, các chi bộ"),
                    _cell("10/2025"),
                    _cell("12/2025"),
                    _cell("Quyết định phê duyệt"),
                ],
                source_pages=[3],
            ),
        ],
        source_pages=[3],
    )
    doc = CanonicalDocument(
        document_id="doc_kehoach",
        tables=[tbl],
        metadata={"title": "Kế hoạch triển khai nhiệm vụ trọng tâm"},
    )

    normalizer = ImplementationPlanRecordNormalizer()
    assert normalizer.supports(doc) is True

    records = normalizer.normalize(doc)
    assert len(records) == 1
    task = records[0]
    assert isinstance(task, ImplementationTaskRecord)
    assert task.task_code == "1.1"
    assert task.category == "Công tác phát triển đội ngũ, tổ chức, nhân sự"
    assert task.lead_unit == "Văn phòng"
    assert task.coordinating_units == ["Đảng ủy", "các chi bộ"]
    assert task.start_date == "10/2025"
    assert task.deliverables == ["Quyết định phê duyệt"]


def test_quality_gate_detects_cross_table_conflicts():
    # Table 1: AI code is 7480107
    tbl1 = CanonicalTable(
        table_id="tbl_main",
        schema_key="k1",
        headers=["Mã ngành", "Tên ngành"],
        rows=[
            CanonicalRow(row_id="r1", cells=[_cell("7480107"), _cell("Trí tuệ nhân tạo")], source_pages=[6]),
        ],
        source_pages=[6],
    )
    # Table 2: AI code is mistakenly listed as 7480207 in appendix
    tbl2 = CanonicalTable(
        table_id="tbl_appendix",
        schema_key="k2",
        headers=["Mã ngành", "Tên ngành"],
        rows=[
            CanonicalRow(row_id="r2", cells=[_cell("7480207"), _cell("Trí tuệ nhân tạo")], source_pages=[13]),
        ],
        source_pages=[13],
    )
    doc = CanonicalDocument(
        document_id="doc_conflict",
        tables=[tbl1, tbl2],
    )

    gate = DataQualityGate()
    report = gate.evaluate(doc)

    assert report.passed is False
    assert any(iss.code == "CONFLICTING_PROGRAM_CODE" for iss in report.issues)
    conflict_issue = next(iss for iss in report.issues if iss.code == "CONFLICTING_PROGRAM_CODE")
    assert conflict_issue.severity == "blocking"
    assert "7480107" in conflict_issue.raw_values
    assert "7480207" in conflict_issue.raw_values


def test_quality_gate_blocks_placeholder_headers_and_duplicate_programs():
    tbl = CanonicalTable(
        table_id="tbl_invalid",
        schema_key="invalid",
        headers=["STT", "Mã ngành", "Tên ngành", "Phương thức", "Cột 5"],
        rows=[
            CanonicalRow(
                row_id="r1",
                cells=[_cell("1"), _cell("7140114"), _cell("Quản lý giáo dục"), _cell("1,2"), _cell("x")],
                source_pages=[2],
            ),
            CanonicalRow(
                row_id="r2",
                cells=[_cell("1"), _cell("7140114"), _cell("Quản lý giáo dục"), _cell("1,2"), _cell("x")],
                source_pages=[3],
            ),
        ],
        source_pages=[2, 3],
    )
    doc = CanonicalDocument(document_id="doc_invalid", tables=[tbl])

    report = DataQualityGate().evaluate(doc)

    assert report.passed is False
    issue_codes = {issue.code for issue in report.issues}
    assert "UNRESOLVED_TABLE_HEADER" in issue_codes
    assert "DUPLICATE_BUSINESS_RECORD" in issue_codes


def test_prepare_domain_records_blocks_invalid_document_before_chunking():
    tbl = CanonicalTable(
        table_id="tbl_invalid",
        schema_key="invalid",
        headers=["STT", "Mã ngành", "Tên ngành", "Phương thức", "Cột 5"],
        rows=[
            CanonicalRow(
                row_id="r1",
                cells=[
                    _cell("1"),
                    _cell("7140114"),
                    _cell("Quản lý giáo dục"),
                    _cell("1,2"),
                    _cell("x"),
                ],
                source_pages=[2],
            )
        ],
        source_pages=[2],
    )
    parsed = ParsedContent(
        raw_text="Nội dung tuyển sinh",
        canonical_document=CanonicalDocument(
            document_id="doc_invalid",
            tables=[tbl],
            metadata={"title": "Thông tin tuyển sinh"},
        ),
    )

    prepared = IngestionService._prepare_domain_records(parsed)

    assert prepared["quality_blocked"] is True
    assert prepared["chunk_drafts"] == []
    assert prepared["facts_data"] == []
    assert prepared["quality_report"]["passed"] is False


def test_prepare_domain_records_creates_atomic_chunks_and_facts():
    tbl = CanonicalTable(
        table_id="tbl_programs",
        schema_key="programs",
        headers=["STT", "Mã ngành", "Tên ngành", "Phương thức", "Chỉ tiêu", "Tổ hợp môn"],
        rows=[
            CanonicalRow(
                row_id="r1",
                cells=[
                    _cell("1"),
                    _cell("7140114"),
                    _cell("Quản lý giáo dục"),
                    _cell("1, 2"),
                    _cell("50"),
                    _cell("Toán, Văn, Anh"),
                ],
                source_pages=[2],
            )
        ],
        source_pages=[2],
    )
    parsed = ParsedContent(
        raw_text="Nội dung tuyển sinh",
        canonical_document=CanonicalDocument(
            document_id="doc_valid",
            tables=[tbl],
            metadata={"title": "Thông tin tuyển sinh"},
        ),
    )

    prepared = IngestionService._prepare_domain_records(parsed)

    assert prepared["quality_blocked"] is False
    assert prepared["domain_record_count"] == 1
    assert len(prepared["chunk_drafts"]) == 1
    assert len(prepared["facts_data"]) >= 3


def test_admissions_record_chunker_is_atomic():
    prog = AdmissionProgramRecord(
        program_code="7480107",
        program_name="Trí tuệ nhân tạo",
        admission_methods=["1", "2", "4"],
        expected_quota=50,
        subject_combinations=[["Toán", "Lý", "Hóa"], ["Toán", "Tin", "Anh"]],
        source_pages=[6],
    )

    chunker = get_chunker("admissions")
    assert isinstance(chunker, AdmissionsRecordChunker)

    chunks = chunker.chunk("", records=[prog])
    assert len(chunks) == 1
    chk = chunks[0]
    assert chk.metadata["entity_key"] == "program:7480107"
    assert "Trí tuệ nhân tạo" in chk.content
    assert "7480107" in chk.content
    assert "Toán - Lý - Hóa" in chk.content


def test_fact_extractor_from_domain_records():
    prog = AdmissionProgramRecord(
        program_code="7480107",
        program_name="Trí tuệ nhân tạo",
        admission_methods=["1", "4"],
        expected_quota=50,
        subject_combinations=[["Toán", "Lý", "Hóa"]],
        source_pages=[6],
    )
    facts = fact_extractor.extract_facts_from_domain_records([prog], "col_ts", "doc_ts")
    assert len(facts) >= 3

    attributes = {f["attribute_name"]: f["attribute_value"] for f in facts}
    assert attributes["Mã ngành"] == "7480107"
    assert attributes["Chỉ tiêu"] == "50"
    assert attributes["Phương thức tuyển sinh"] == "1, 4"
    assert attributes["Tổ hợp xét tuyển"] == "Toán - Lý - Hóa"


def test_fact_extractor_rebuilds_facts_from_verified_markdown_table():
    facts = fact_extractor.extract_from_verified_markdown_pages(
        [
            {
                "page_number": 2,
                "markdown_content": """| Mã ngành | Tên ngành | Chỉ tiêu |
| --- | --- | --- |
| 7140114 | Quản lý giáo dục | 50 |""",
            }
        ],
        "col_admissions",
        "doc_verified",
    )

    attributes = {fact["attribute_name"]: fact["attribute_value"] for fact in facts}
    assert attributes["Mã ngành"] == "7140114"
    assert attributes["Chỉ tiêu"] == "50"
