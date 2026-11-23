"""Unit tests for public chatbot security: origin whitelist, proxy IP extraction, honeypot and time-gate."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError
from starlette.datastructures import Headers

from qnu.domains.publications.public_service import (
    create_session,
    extract_client_ip,
    turn,
)
from qnu.domains.publications.schemas import (
    PublicationConfig,
    PublicSessionRequest,
    PublicTurnRequest,
    normalize_origin,
)
from qnu.platform.errors import AppException


def test_normalize_origin_valid():
    assert normalize_origin("https://qnu.edu.vn") == "https://qnu.edu.vn"
    assert normalize_origin("http://localhost:3000") == "http://localhost:3000"
    assert (
        normalize_origin("https://sub.qnu.edu.vn:8443/test/path?foo=1#bar")
        == "https://sub.qnu.edu.vn:8443"
    )
    assert normalize_origin("https://QNU.EDU.VN/") == "https://qnu.edu.vn"
    assert normalize_origin("qnu.edu.vn") == "https://qnu.edu.vn"
    assert normalize_origin("localhost:3000") == "http://localhost:3000"
    assert normalize_origin("") == ""


def test_normalize_origin_invalid():
    with pytest.raises(ValueError, match="không hợp lệ"):
        normalize_origin("ftp://qnu.edu.vn")
    with pytest.raises(ValueError, match="không hợp lệ"):
        normalize_origin("javascript:alert(1)")
    with pytest.raises(ValueError, match="không hợp lệ"):
        normalize_origin("invalid domain with spaces")


def test_publication_config_origins_cleaning():
    config = PublicationConfig(
        slug="test-bot",
        display_name="Test Bot",
        allowed_embed_origins=[
            "https://qnu.edu.vn",
            "https://qnu.edu.vn/",
            "qnu.edu.vn",
            "http://localhost:3000",
            "localhost:3000",
            "",
            "   ",
        ],
    )
    assert config.allowed_embed_origins == [
        "https://qnu.edu.vn",
        "http://localhost:3000",
    ]


def test_publication_config_origins_none_and_string():
    config_none = PublicationConfig(
        slug="test-bot",
        display_name="Test Bot",
        allowed_embed_origins=None,
    )
    assert config_none.allowed_embed_origins == []

    config_str = PublicationConfig(
        slug="test-bot",
        display_name="Test Bot",
        allowed_embed_origins="https://qnu.edu.vn\nhttp://localhost:3000",
    )
    assert config_str.allowed_embed_origins == [
        "https://qnu.edu.vn",
        "http://localhost:3000",
    ]


def test_publication_config_origins_invalid_raises():
    with pytest.raises(ValidationError):
        PublicationConfig(
            slug="test-bot",
            display_name="Test Bot",
            allowed_embed_origins=["invalid-domain"],
        )


def _make_request(headers: dict[str, str] | None = None, host: str | None = None):
    req = SimpleNamespace()
    req.headers = Headers(headers or {})
    if host:
        req.client = SimpleNamespace(host=host)
    else:
        req.client = None
    return req


def test_extract_client_ip_cf_connecting_ip():
    req = _make_request(
        headers={"cf-connecting-ip": "203.0.113.195", "x-forwarded-for": "198.51.100.1"},
        host="10.0.0.1",
    )
    assert extract_client_ip(req) == "203.0.113.195"


def test_extract_client_ip_x_forwarded_for():
    req = _make_request(
        headers={"x-forwarded-for": "198.51.100.1, 10.0.0.2, 10.0.0.3"},
        host="10.0.0.1",
    )
    assert extract_client_ip(req) == "198.51.100.1"


def test_extract_client_ip_direct_host():
    req = _make_request(host="192.168.1.50")
    assert extract_client_ip(req) == "192.168.1.50"


def test_extract_client_ip_unknown():
    req = _make_request()
    assert extract_client_ip(req) == "unknown"


@pytest.mark.asyncio
async def test_create_session_honeypot_rejects_bot():
    db = AsyncMock()
    body = PublicSessionRequest(website="https://spambot.example.com")
    with pytest.raises(AppException) as exc_info:
        await create_session(db, "test-bot", "client-123", body=body)
    assert exc_info.value.code == "public_chat_bot_detected"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_turn_honeypot_rejects_bot():
    db = AsyncMock()
    blob = AsyncMock()
    embedding = AsyncMock()
    vectors = AsyncMock()
    chat = AsyncMock()
    req = PublicTurnRequest(
        session_id="a" * 24,
        question="Học phí bao nhiêu?",
        website="https://spambot.example.com",
    )
    with pytest.raises(AppException) as exc_info:
        await turn(
            db=db,
            blob=blob,
            embedding=embedding,
            vectors=vectors,
            chat=chat,
            reranker=None,
            slug="test-bot",
            req=req,
            requester="client-123",
        )
    assert exc_info.value.code == "public_chat_bot_detected"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_turn_time_gate_first_turn_too_fast():
    db = AsyncMock()
    blob = AsyncMock()
    embedding = AsyncMock()
    vectors = AsyncMock()
    chat = AsyncMock()
    req = PublicTurnRequest(
        session_id="a" * 24,
        question="Học phí bao nhiêu?",
    )
    mock_pub = SimpleNamespace(
        id="pub-1",
        max_turns_per_session=10,
        daily_token_budget=None,
    )

    with (
        patch(
            "qnu.domains.publications.public_service._publication",
            AsyncMock(return_value=(mock_pub, True)),
        ),
        patch(
            "qnu.domains.publications.public_service.get_json",
            AsyncMock(
                return_value={
                    "publication_id": "pub-1",
                    "turns": 0,
                    "created_at": time.time() - 0.2,
                }
            ),
        ),
    ):
        with pytest.raises(AppException) as exc_info:
            await turn(
                db=db,
                blob=blob,
                embedding=embedding,
                vectors=vectors,
                chat=chat,
                reranker=None,
                slug="test-bot",
                req=req,
                requester="client-123",
            )
        assert exc_info.value.code == "public_chat_too_fast"
        assert exc_info.value.status_code == 429
