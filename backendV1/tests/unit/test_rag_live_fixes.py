"""Unit tests for prompt-echo guard, parenthesized table subject matching, and sub-section bullet lists."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from qnu.domains.rag.answer.fallback import FallbackMessage, is_prompt_echo
from qnu.domains.rag.answer.structure_context import _groups
from qnu.domains.rag.answer.table_selection import select_catalog


def test_is_prompt_echo_blocks_leaked_system_directives_and_allows_normal_fallback():
    leaked = (
        "Chưa tìm thấy thông tin phù hợp trong nguồn hiện có và gợi ý người dùng nêu rõ tên văn bản, "
        "điều khoản, năm hoặc bổ sung tài liệu. Không nêu tên tài liệu, điều khoản, số liệu, kết luận "
        "hay bất kỳ dữ kiện nào; không khẳng định cả kho không có; không hứa hẹn; không citation, "
        "Markdown hoặc HTML. Với status answered, message là null."
    )
    assert is_prompt_echo(leaked) is True
    with pytest.raises(ValidationError):
        FallbackMessage(message=leaked)

    clean = (
        "Hiện tại mình chưa tìm thấy thông tin về mức học phí trong tài liệu tuyển sinh được cung cấp. "
        "Bạn vui lòng bổ sung quyết định học phí tương ứng để mình hỗ trợ chính xác hơn."
    )
    assert is_prompt_echo(clean) is False
    assert FallbackMessage(message=clean).message == clean


def test_select_catalog_matches_base_subject_with_parenthetical_qualifier():
    source = SimpleNamespace(
        evidence_id="E1",
        chunk_id="ch_1",
        document_id="doc_1",
        version_id="ver_1",
        publication_decision_id="pub_1",
        structure={"source_table_citation": "ocr_1:ev_p005_b001"},
    )
    cells = {
        "tables": [
            {
                "evidence_id": "E1",
                "cells": [
                    {
                        "cell_id": "E1:r1:k1",
                        "subject_labels": ["Công nghệ thông tin (An toàn, an ninh mạng)"],
                        "value": "15",
                    },
                    {
                        "cell_id": "E1:r2:k1",
                        "subject_labels": ["Công nghệ thông tin (giảng dạy bằng tiếng Anh)"],
                        "value": "15",
                    },
                    {
                        "cell_id": "E1:r3:k1",
                        "subject_labels": ["Kỹ thuật phần mềm"],
                        "value": "15",
                    },
                ],
            }
        ],
        "issues": [],
    }
    res = select_catalog(
        cells,
        [source],
        "Ngưỡng điểm sàn năm 2026 của ngành Công nghệ thông tin là bao nhiêu?",
        [],
    )
    kept_ids = [c["cell_id"] for c in res["tables"][0]["cells"]]
    assert kept_ids == ["E1:r1:k1", "E1:r2:k1"]
    assert res["selection"]["matched_families"] == 1


def test_bullet_group_captures_numbered_subsection_bullets_pt1_to_pt5():
    sec = "ocr:ev_sec_ii"
    records = [
        {"ref": sec, "section": sec, "is_table": False, "text": "II. Tuyển sinh đại học CHÍNH QUY", "ids": ["c0"]},
        {"ref": "ocr:b21", "section": sec, "is_table": False, "text": "2. Phương thức tuyển sinh:", "ids": ["c1"]},
        {"ref": "ocr:b22", "section": sec, "is_table": False, "text": "+ Phương thức 1 (PT1 - mã 100): THPT", "ids": ["c2"]},
        {"ref": "ocr:b23", "section": sec, "is_table": False, "text": "+ Phương thức 2 (PT2 - mã 200): Học bạ", "ids": ["c3"]},
        {"ref": "ocr:b24", "section": sec, "is_table": False, "text": "+ Phương thức 3 (PT3 - mã 402A): ĐGNL HCM", "ids": ["c4"]},
        {"ref": "ocr:b25", "section": sec, "is_table": False, "text": "+ Phương thức 4 (PT4 - mã 402B): ĐGNL HN", "ids": ["c5"]},
        {"ref": "ocr:b26", "section": sec, "is_table": False, "text": "+ Phương thức 5 (PT5 - mã 405): Năng khiếu", "ids": ["c6"]},
        {"ref": "ocr:b27", "section": sec, "is_table": False, "text": "Ngoài ra, thực hiện Xét tuyển thẳng.", "ids": ["c7"]},
        {"ref": "ocr:b28", "section": sec, "is_table": False, "text": "3. Quy tắc quy đổi điểm:", "ids": ["c8"]},
    ]
    groups = _groups(records)
    bullet_groups = [g for kind, g in groups if kind == "bullet_list"]
    assert len(bullet_groups) == 1
    captured_refs = [r["ref"] for r in bullet_groups[0]]
    assert captured_refs == [
        "ocr:b21",
        "ocr:b22",
        "ocr:b23",
        "ocr:b24",
        "ocr:b25",
        "ocr:b26",
        "ocr:b27",
    ]
