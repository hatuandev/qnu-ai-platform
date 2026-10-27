"""Nemotron wording must not be replaced by a second spelling/grammar pass."""

import copy
import time
from unittest.mock import AsyncMock

import pytest

from app.modules.ocr.cleaner import clean_ocr_table_syntax
from app.modules.ocr.service import OCRService


def test_table_cleanup_preserves_provider_wording_and_only_repairs_structure():
    source = "| Mục | Nội dung |\n| --- | --- |\n| --- | --- |\n| 1 | số chỉ hiệu năng; kí kết; kí hợp đồng; năm 2026 |"
    cleaned = clean_ocr_table_syntax(source)
    assert "số chỉ hiệu năng; kí kết; kí hợp đồng; năm 2026" in cleaned
    assert cleaned.count("| --- | --- |") == 1


@pytest.mark.asyncio
async def test_nemotron_response_keeps_words_numbers_and_raw_evidence():
    text = "Năm 2026: số chỉ hiệu năng 5.173; kí hợp đồng; chưa rõ —; mã QNU-0007."
    page = {"page_number": 1, "extracted_text": text, "confidence": 0,
            "word_count": len(text.split()), "line_count": 1, "blocks": []}
    result = {"engine_used": "nemotron_parse", "raw_text": text, "pages": [page],
              "total_pages": 1, "overall_confidence": 0, "raw_payload": {"text": text}}
    original = copy.deepcopy(result)
    response = await OCRService()._build_response(AsyncMock(), result, "literal.pdf", "tenant", time.perf_counter(), False)
    assert response.raw_text == text
    assert response.pages[0].extracted_text == text
    assert response.raw_evidence["pages"] == original["pages"]
    assert "post_correction" not in response.model_dump()
