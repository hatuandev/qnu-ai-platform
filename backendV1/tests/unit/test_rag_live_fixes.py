"""Unit tests for prompt-echo guard, parenthesized table subject matching, and sub-section bullet lists."""

from __future__ import annotations

import unicodedata
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from qnu.domains.rag.answer.fallback import (
    SAFE_FALLBACK_MESSAGE,
    FallbackMessage,
    is_prompt_echo,
)
from qnu.domains.rag.answer.fallback import compose as compose_fallback
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
    # NFD decomposed Unicode must also be detected via NFC normalization
    assert is_prompt_echo(unicodedata.normalize("NFD", leaked)) is True
    with pytest.raises(ValidationError):
        FallbackMessage(message=leaked)

    clean = (
        "Hiện tại mình chưa tìm thấy thông tin về mức học phí trong tài liệu tuyển sinh được cung cấp. "
        "Bạn vui lòng bổ sung quyết định học phí tương ứng để mình hỗ trợ chính xác hơn."
    )
    assert is_prompt_echo(clean) is False
    assert FallbackMessage(message=clean).message == clean


@pytest.mark.asyncio
async def test_compose_fallback_returns_safe_static_message_on_prompt_echo():
    runtime = SimpleNamespace(
        provider_id="prov_1",
        model_name="qwen-27b",
        inference_configuration_hash=lambda task: "hash_1",
    )
    budget = SimpleNamespace(total_reserved_tokens=200)
    usage = SimpleNamespace(id="usg_1")
    leaked_json = '{"message": "Không nêu tên tài liệu, không khẳng định cả kho không có."}'
    chat = MagicMock()
    chat.complete = AsyncMock(return_value=SimpleNamespace(content=leaked_json, total_tokens=15))
    db = AsyncMock()

    with (
        patch("qnu.domains.rag.answer.fallback.prepare_chat_request", AsyncMock(return_value=(runtime, SimpleNamespace(), budget))),
        patch("qnu.domains.rag.answer.fallback.usage_service.reserve", AsyncMock(return_value=usage)),
        patch("qnu.domains.rag.answer.fallback.usage_service.settle", AsyncMock()),
        patch("qnu.domains.rag.answer.fallback.resolve_chat_runtime", AsyncMock(return_value=runtime)),
        patch("qnu.domains.rag.answer.fallback.bind_usage", side_effect=lambda req, uid: req),
    ):
        msg, info = await compose_fallback(
            db, chat, MagicMock(), "ws_1", "prov_1", "Học phí?", "model_abstained", "", idempotency="ans_1"
        )

    assert msg == SAFE_FALLBACK_MESSAGE
    assert info["source"] == "safe_static_fallback"
    assert info["echo_blocked"] is True


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


def test_select_catalog_single_syllable_subject_nested_parens_and_generic_guard():
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
                        "subject_labels": ["Luật (Chính quy (hệ đại trà))"],
                        "value": "18",
                    },
                    {
                        "cell_id": "E1:r2:k1",
                        "subject_labels": ["Dược (Chất lượng cao)"],
                        "value": "21",
                    },
                    {
                        "cell_id": "E1:r3:k1",
                        "subject_labels": ["Khu vực (KV1)"],
                        "value": "0.75",
                    },
                ],
            }
        ],
        "issues": [],
    }
    # Single-syllable subject with explicit "ngành Luật" matches properly
    res_luat = select_catalog(
        cells, [source], "Điểm chuẩn ngành Luật năm 2026 là bao nhiêu?", []
    )
    assert [c["cell_id"] for c in res_luat["tables"][0]["cells"]] == ["E1:r1:k1"]

    # Generic 2-word phrase ("khu vực") in a general question must NOT narrow out other rows
    res_generic = select_catalog(
        cells, [source], "Điểm chuẩn các ngành tại khu vực miền Trung là bao nhiêu?", []
    )
    assert len(res_generic["tables"][0]["cells"]) == 3


def test_bullet_group_stops_before_subheading_or_multiple_trailing_prose_paragraphs():
    sec = "ocr:ev_sec_ii"
    records = [
        {"ref": sec, "section": sec, "is_table": False, "text": "II. Quy định chung", "ids": ["c0"]},
        {"ref": "ocr:b1", "section": sec, "is_table": False, "text": "2. Điều kiện dự tuyển:", "ids": ["c1"]},
        {"ref": "ocr:b2", "section": sec, "is_table": False, "text": "- Tốt nghiệp THPT", "ids": ["c2"]},
        {"ref": "ocr:b3", "section": sec, "is_table": False, "text": "- Đủ sức khỏe học tập", "ids": ["c3"]},
        {"ref": "ocr:b4", "section": sec, "is_table": False, "text": "Ghi chú thêm cho mục trên.", "ids": ["c4"]},
        {"ref": "ocr:b5", "section": sec, "is_table": False, "text": "Đoạn văn bản bình thường tiếp theo không thuộc danh sách.", "ids": ["c5"]},
        {"ref": "ocr:b6", "section": sec, "is_table": False, "text": "Lưu ý về lệ phí:", "ids": ["c6"]},
    ]
    bullet_groups = [g for kind, g in _groups(records) if kind == "bullet_list"]
    assert len(bullet_groups) == 1
    assert [r["ref"] for r in bullet_groups[0]] == ["ocr:b1", "ocr:b2", "ocr:b3", "ocr:b4"]
