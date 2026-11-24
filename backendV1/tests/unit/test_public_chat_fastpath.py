"""Unit tests for public chatbot social-turn detection and model selection."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.publications import public_service
from qnu.domains.publications.public_service import (
    is_pure_smalltalk,
    list_public_chat_models,
    resolve_public_chat_provider,
)
from qnu.platform.errors import AppException


@pytest.mark.parametrize(
    "text",
    [
        "xin chào",
        "Xin chào!",
        "chào bạn",
        "Chào trợ lý ạ",
        "chào buổi sáng",
        "alo",
        "hello",
        "Hi!",
        "cảm ơn",
        "Cảm ơn bạn nhiều nhé!",
        "ok cám ơn ạ",
        "thank you",
        "tạm biệt",
        "bye bye",
    ],
)
def test_is_pure_smalltalk_detects_pure_social_messages(text: str):
    assert is_pure_smalltalk(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "Xin chào, điểm chuẩn ngành CNTT năm 2025 là bao nhiêu?",
        "Chào bạn cho mình hỏi học phí kỳ này",
        "Cảm ơn bạn, vậy tổ hợp xét tuyển ngành Luật là gì?",
        "Điểm chuẩn trúng tuyển các năm gần nhất?",
        "xin chào 2025",
        "Em đạt 15 điểm Toán Văn Địa có xét học bạ được không?",
        "tôi muốn làm 1 đơn xin nghỉ phép có được ko ?",
        "",
        "   ",
    ],
)
def test_is_pure_smalltalk_ignores_substantive_questions(text: str):
    assert is_pure_smalltalk(text) is False


@pytest.mark.asyncio
async def test_public_chat_model_listing_and_resolution(monkeypatch):
    fake_providers = [
        SimpleNamespace(
            id="prv_qwen",
            model_name="qwen3.8-27b-q4",
            capabilities=["chat"],
        ),
        SimpleNamespace(
            id="prv_luna",
            model_name="cx/gpt-6-luna",
            capabilities=["chat"],
        ),
        SimpleNamespace(
            id="prv_embed",
            model_name="bge-m3",
            capabilities=["embedding"],
        ),
    ]
    monkeypatch.setattr(
        public_service.provider_service,
        "list",
        AsyncMock(return_value=fake_providers),
    )

    options, default_name, mapping = await list_public_chat_models(None, "prv_qwen")
    assert [opt.model_name for opt in options] == ["qwen3.8-27b-q4", "cx/gpt-6-luna"]
    assert [opt.label for opt in options] == ["qwen3.8-27b-q4", "gpt-6-luna"]
    assert default_name == "qwen3.8-27b-q4"
    assert options[0].is_default is True
    assert options[1].is_default is False
    assert mapping == {"qwen3.8-27b-q4": "prv_qwen", "cx/gpt-6-luna": "prv_luna"}

    assistant = SimpleNamespace(chat_provider_id="prv_qwen")

    # Fallback to assistant default when model_name is omitted
    pid, mname = await resolve_public_chat_provider(None, assistant, None)
    assert (pid, mname) == ("prv_qwen", "qwen3.8-27b-q4")

    # Switching to another active chat model resolves its provider_id
    pid2, mname2 = await resolve_public_chat_provider(None, assistant, "cx/gpt-6-luna")
    assert (pid2, mname2) == ("prv_luna", "cx/gpt-6-luna")

    # Non-chat or unknown model is rejected with 422
    with pytest.raises(AppException) as exc_info:
        await resolve_public_chat_provider(None, assistant, "bge-m3")
    assert exc_info.value.code == "public_chat_model_unavailable"
    assert exc_info.value.status_code == 422
