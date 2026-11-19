"""Unit tests for Slice 6B: Partial Amendments Resolution, Scope Facets & Non-tabular Blocks.

Verifies:
1. Detection of amendment and transition inquiries.
2. Cross-document partial amendment resolution (superseded vs active amending regulations).
3. Historical comparison mode vs standard lookup mode.
4. Dynamic Scope Facets filtering (department, audience, education level).
5. MetadataFilter & matches_metadata lifecycle governance.
6. Formatting for non-tabular blocks (procedure, form_template, visual_desc).
"""


from qnu.domains.knowledge.metadata import (
    MetadataFilter,
    matches_metadata,
)
from qnu.domains.rag.answer.amendments import (
    detect_amendment_inquiry,
    filter_by_scope_facets,
    format_form_template_block,
    format_procedure_block,
    format_visual_desc_block,
    match_scope_facets,
    resolve_amendments,
)


def test_detect_amendment_inquiry():
    assert detect_amendment_inquiry("Quy định này đã được sửa đổi bổ sung như thế nào?") is True
    assert detect_amendment_inquiry("Điều 5 đã bị thay thế bởi văn bản nào?") is True
    assert detect_amendment_inquiry("Quy chế này trước đây quy định ra sao?") is True
    assert detect_amendment_inquiry("Quy định mới áp dụng từ ngày nào?") is True
    assert detect_amendment_inquiry("So với quy định cũ thì điều kiện tốt nghiệp có gì khác?") is True

    # Standard lookup
    assert detect_amendment_inquiry("Điểm chuẩn ngành Công nghệ thông tin năm 2026") is False
    assert detect_amendment_inquiry("Học phí ngành Sư phạm Toán là bao nhiêu?") is False


def test_resolve_amendments_standard_lookup():
    # Document A (2024): Điều 5 bị thay thế
    source_old = {
        "evidence_id": "E_OLD",
        "citation": "doc_2024:dieu_5",
        "source_passages": [{"text": "Sinh viên nộp chứng chỉ tiếng Anh B1 trước khi tốt nghiệp."}],
        "structure": {
            "lifecycle": {
                "status": "superseded",
                "effective_from": "2024-09-01",
                "superseded_by_ref": "E_AMEND",
            }
        },
    }
    # Document B (2026): Sửa Điều 5 của Document A
    source_amend = {
        "evidence_id": "E_AMEND",
        "citation": "doc_2026:dieu_5",
        "source_passages": [{"text": "Sinh viên nộp chứng chỉ tiếng Anh B2 trước khi tốt nghiệp."}],
        "structure": {
            "lifecycle": {
                "status": "amended",
                "effective_from": "2026-01-01",
                "amends_ref": "E_OLD",
            }
        },
    }

    resolved, trace = resolve_amendments([source_old, source_amend], is_amendment_inquiry=False)
    assert trace["amendments_detected"] is True
    assert trace["is_amendment_inquiry"] is False

    # Old source must be tagged with replacement notice
    old_text = resolved[0]["source_passages"][0]["text"]
    assert "ĐÃ BỊ THAY THẾ/SỬA ĐỔI" in old_text
    assert "E_AMEND" in old_text
    assert "2026-01-01" in old_text

    # Amending source must be tagged with active amendment header
    amend_text = resolved[1]["source_passages"][0]["text"]
    assert "QUY ĐỊNH SỬA ĐỔI / HIỆN HÀNH" in amend_text
    assert "E_OLD" in amend_text


def test_resolve_amendments_historical_inquiry():
    source_old = {
        "evidence_id": "E_OLD",
        "citation": "doc_2024:dieu_5",
        "source_passages": [{"text": "Mức hỗ trợ học tập là 500.000đ/tháng."}],
        "structure": {
            "lifecycle": {
                "status": "superseded",
                "effective_from": "2024-09-01",
                "superseded_by_ref": "E_AMEND",
            }
        },
    }
    source_amend = {
        "evidence_id": "E_AMEND",
        "citation": "doc_2026:dieu_5",
        "source_passages": [{"text": "Mức hỗ trợ học tập điều chỉnh thành 800.000đ/tháng."}],
        "structure": {
            "lifecycle": {
                "status": "active",
                "effective_from": "2026-01-01",
                "amends_ref": "E_OLD",
            }
        },
    }

    resolved, trace = resolve_amendments([source_old, source_amend], is_amendment_inquiry=True)
    assert trace["amendments_detected"] is True
    assert trace["is_amendment_inquiry"] is True

    # In historical inquiry, old regulation is explicitly preserved with history note
    old_text = resolved[0]["source_passages"][0]["text"]
    assert "[QUY ĐỊNH CŨ" in old_text
    assert "E_AMEND" in old_text


def test_scope_facets_matching_and_filtering():
    facets_dao_tao = {
        "don_vi": "Phòng Đào tạo",
        "doi_tuong": "Sinh viên chính quy",
        "he_dao_tao": "Đại học",
    }
    facets_khao_thi = {
        "don_vi": "Phòng Khảo thí",
        "doi_tuong": "Sinh viên chính quy",
        "he_dao_tao": "Đại học",
    }

    assert match_scope_facets(facets_dao_tao, {"don_vi": "Phòng Đào tạo"}) is True
    assert match_scope_facets(facets_dao_tao, {"don_vi": "phòng đào tạo"}) is True
    assert match_scope_facets(facets_dao_tao, {"don_vi": "Phòng Khảo thí"}) is False
    assert match_scope_facets(facets_dao_tao, {"doi_tuong": "Sau đại học"}) is False
    assert (
        match_scope_facets(
            facets_dao_tao, {"don_vi": "Phòng Đào tạo", "doi_tuong": "Sinh viên chính quy"}
        )
        is True
    )

    sources = [
        {"evidence_id": "S1", "structure": {"scope_facets": facets_dao_tao}},
        {"evidence_id": "S2", "structure": {"scope_facets": facets_khao_thi}},
    ]
    filtered = filter_by_scope_facets(sources, {"don_vi": "Phòng Đào tạo"})
    assert len(filtered) == 1
    assert filtered[0]["evidence_id"] == "S1"


def test_matches_metadata_with_lifecycle_governance():
    # Superseded unit
    superseded_struct = {
        "retrieval_metadata": [
            {
                "target": "section:1",
                "evidence": [{"citation": "c1", "quote": "q1"}],
                "values": {
                    "lifecycle": {
                        "status": "superseded",
                        "effective_from": "2024-09-01",
                        "superseded_by_ref": "doc_2026:1",
                    }
                },
            }
        ]
    }
    # Active unit
    active_struct = {
        "retrieval_metadata": [
            {
                "target": "section:1",
                "evidence": [{"citation": "c2", "quote": "q2"}],
                "values": {
                    "lifecycle": {
                        "status": "active",
                        "effective_from": "2026-01-01",
                        "amends_ref": "doc_2024:1",
                    }
                },
            }
        ]
    }

    # Default filter (include_superseded=False): superseded must NOT match
    default_filter = MetadataFilter()
    assert matches_metadata(superseded_struct, default_filter) is False
    assert matches_metadata(active_struct, default_filter) is True

    # Filter with include_superseded=True: superseded matches
    history_filter = MetadataFilter(include_superseded=True)
    assert matches_metadata(superseded_struct, history_filter) is True
    assert matches_metadata(active_struct, history_filter) is True

    # Specific lifecycle_status filter
    active_only_filter = MetadataFilter(lifecycle_status="active")
    assert matches_metadata(superseded_struct, active_only_filter) is False
    assert matches_metadata(active_struct, active_only_filter) is True


def test_matches_metadata_with_scope_facets():
    struct_dao_tao = {
        "retrieval_metadata": [
            {
                "target": "section:1",
                "evidence": [{"citation": "c1", "quote": "q1"}],
                "values": {
                    "scope_facets": {"don_vi": "Phòng Đào tạo", "he_dao_tao": "Đại học"}
                },
            }
        ]
    }

    filter_dao_tao = MetadataFilter(scope_facets={"don_vi": "Phòng Đào tạo"})
    filter_khao_thi = MetadataFilter(scope_facets={"don_vi": "Phòng Khảo thí"})

    assert matches_metadata(struct_dao_tao, filter_dao_tao) is True
    assert matches_metadata(struct_dao_tao, filter_khao_thi) is False


def test_non_tabular_formatters():
    # 1. Procedure block
    steps = [
        "Nộp đơn xin chuyển ngành tại Văn phòng một cửa.",
        "Phòng Đào tạo thẩm định hồ sơ trong vòng 3 ngày làm việc.",
        "Hiệu trưởng phê duyệt và ban hành quyết định.",
    ]
    proc_md = format_procedure_block("Bước 1 đến 3", steps, title="Chuyển ngành học")
    assert "QUY TRÌNH: Chuyển ngành học" in proc_md
    assert "Bước 1 đến 3" in proc_md
    assert "**Bước 1:** Nộp đơn" in proc_md
    assert "**Bước 2:** Phòng Đào tạo" in proc_md
    assert "**Bước 3:** Hiệu trưởng" in proc_md

    # 2. Form template block
    form_md = format_form_template_block(
        form_name="Đơn xin hoãn thi học kỳ",
        form_code="BM-03/KT",
        attachment_ref="Phụ lục III",
        download_url="https://qnu.edu.vn/bieu-mau/bm-03.docx",
    )
    assert "BIỂU MẪU: Đơn xin hoãn thi học kỳ" in form_md
    assert "`BM-03/KT`" in form_md
    assert "Phụ lục III" in form_md
    assert "[Tải tại đây](https://qnu.edu.vn/bieu-mau/bm-03.docx)" in form_md

    # 3. Visual description block
    mermaid = """graph TD
A[Thí sinh nộp hồ sơ] --> B{Đạt ngưỡng?}
B -- Có --> C[Công nhận trúng tuyển]
B -- Không --> D[Thông báo không đạt]"""
    visual_md = format_visual_desc_block(
        diagram_title="Lưu đồ xét tuyển sớm",
        description="Quy trình 3 bước từ nộp hồ sơ, kiểm tra ngưỡng đến thông báo kết quả.",
        mermaid_code=mermaid,
        source_page=12,
    )
    assert "SƠ ĐỒ / LƯU ĐỒ: Lưu đồ xét tuyển sớm" in visual_md
    assert "Trang nguồn: 12" in visual_md
    assert "```mermaid" in visual_md
    assert "Thí sinh nộp hồ sơ" in visual_md
