"""Provider types kept executable: chat-only local runtimes replace dead OCR placeholders."""

import pytest
from pydantic import ValidationError

from qnu.domains.modelops.registry import TRANSPORTS, transport_for
from qnu.domains.modelops.schemas import ProviderCreateRequest


def request(provider_type: str) -> dict:
    return {
        "name": "Local chat runtime",
        "provider_type": provider_type,
        "base_url": "http://127.0.0.1:11434/v1",
        "model_name": "gpt-oss:120b",
        "capabilities": ["chat"],
    }


def test_registry_exposes_the_local_chat_runtimes_only_as_chat():
    assert transport_for("ollama").protocols == {"chat": "chat_completions"}
    assert transport_for("llamacpp").protocols == {"chat": "chat_completions"}
    exposed = {item.provider_type for item in TRANSPORTS}
    assert "nemotron" not in exposed and "paddleocr" not in exposed


@pytest.mark.parametrize("provider_type", ["ollama", "llamacpp"])
def test_local_chat_runtimes_accept_a_chat_provider(provider_type):
    assert ProviderCreateRequest(**request(provider_type)).provider_type == provider_type


@pytest.mark.parametrize("provider_type", ["nemotron", "paddleocr"])
def test_removed_provider_types_are_rejected(provider_type):
    with pytest.raises(ValidationError):
        ProviderCreateRequest(**request(provider_type))
