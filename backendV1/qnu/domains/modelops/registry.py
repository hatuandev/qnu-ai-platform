"""Executable protocol metadata shared with the admin UI, not model marketing claims."""

from pydantic import BaseModel


class ProviderTransport(BaseModel):
    provider_type: str
    label: str
    protocols: dict[str, str]
    discovery: bool
    structured_output: str = "not_supported"
    streaming: bool = False
    responses_api: bool = False
    tools: bool = False
    image_input: list[str] = []
    multi_item_input: list[str] = []
    metadata_basis: str = "adapter_contract"


TRANSPORTS = (
    ProviderTransport(
        provider_type="mineru",
        label="MinerU PDF OCR",
        protocols={"ocr": "mineru_tasks"},
        discovery=False,
        multi_item_input=["ocr_pdf_pages"],
    ),
    ProviderTransport(
        provider_type="openai_compatible",
        label="OpenAI compatible",
        protocols={
            "chat": "chat_completions",
            "embedding": "openai_dense",
            "rerank": "rerank",
            "ocr": "nemotron_chat_completions",
        },
        discovery=True,
        image_input=["ocr_png"],
        multi_item_input=["embedding", "rerank"],
        structured_output="request_supported_provider_unverified",
    ),
    ProviderTransport(
        provider_type="local",
        label="Local / vLLM",
        protocols={
            "chat": "chat_completions",
            "embedding": "openai_dense",
            "rerank": "rerank",
            "ocr": "nemotron_chat_completions",
        },
        discovery=True,
        image_input=["ocr_png"],
        multi_item_input=["embedding", "rerank"],
        structured_output="request_supported_provider_unverified",
    ),
    ProviderTransport(
        provider_type="nemotron",
        label="Nemotron",
        protocols={"ocr": "nemotron_chat_completions"},
        discovery=True,
        image_input=["ocr_png"],
    ),
    ProviderTransport(
        provider_type="gemini", label="Gemini (chưa có adapter)", protocols={}, discovery=False
    ),
    ProviderTransport(
        provider_type="paddleocr",
        label="PaddleOCR (chưa có adapter)",
        protocols={},
        discovery=False,
    ),
)


def transport_for(provider_type: str) -> ProviderTransport:
    return next(item for item in TRANSPORTS if item.provider_type == provider_type)
