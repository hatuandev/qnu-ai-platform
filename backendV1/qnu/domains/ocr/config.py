"""Versioned, pinned configuration of one OCR processing run.

Everything that can change the produced bytes is part of the fingerprint: renderer
and DPI, prompt and output limits, processor version. A run keeps its fingerprint
forever, so a later deployment cannot silently reinterpret stored evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qnu.platform.config import Settings
from qnu.platform.errors import AppException

PROCESSOR_VERSION = "qnu-ocr/v1"
PROMPT_VERSION = "nemotron-parse/v1"
CANONICAL_SCHEMA = "qnu.ocr.document/v1"
MANIFEST_SCHEMA = "qnu.ocr.manifest/v1"
MARKDOWN_VERSION = "qnu.ocr.markdown/v1"
TABLE_LAYOUT_VERSION = "nemotron-tabular/v1"

OCR_PROMPT = "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>"

SUPPORTED_PROCESSING_EXTENSIONS = (".pdf", ".docx")


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    """Immutable snapshot of the settings that shape the artifacts."""

    dpi: int
    max_pages: int
    max_page_bytes: int
    max_output_tokens: int
    prompt_version: str
    processor_version: str
    table_layout_version: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        material = json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


def processing_config(settings: Settings) -> ProcessingConfig:
    return ProcessingConfig(
        dpi=settings.OCR_RENDER_DPI,
        max_pages=settings.OCR_MAX_PAGES,
        max_page_bytes=settings.OCR_MAX_PAGE_BYTES,
        max_output_tokens=settings.OCR_MAX_OUTPUT_TOKENS,
        prompt_version=PROMPT_VERSION,
        processor_version=PROCESSOR_VERSION,
        table_layout_version=TABLE_LAYOUT_VERSION,
    )


def config_from_run(payload: dict) -> ProcessingConfig:
    """Rebuild the pinned config from a stored run.

    A stored run must be replayable with the settings it was created under, so a
    missing or malformed key is a hard failure with its own code rather than a
    silent fallback to today's defaults.
    """
    renderer = payload.get("renderer") or {}
    limits = payload.get("ocr") or {}
    try:
        return ProcessingConfig(
            dpi=int(renderer["dpi"]),
            max_pages=int(renderer["max_pages"]),
            max_page_bytes=int(limits["max_page_bytes"]),
            max_output_tokens=int(limits["max_output_tokens"]),
            prompt_version=str(limits["prompt_version"]),
            processor_version=str(limits["processor_version"]),
            table_layout_version=str(limits["table_layout_version"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AppException(
            "Cấu hình đã ghim của lượt xử lý không đọc được.",
            code="processing_config_invalid",
            status_code=409,
        ) from exc


def config_payload(config: ProcessingConfig) -> dict[str, object]:
    """Stored shape of a run config; ``provider`` is filled once a worker resolves it."""
    return {
        "renderer": {
            "dpi": config.dpi,
            "max_pages": config.max_pages,
            "converter": "pymupdf-story",
        },
        "ocr": {
            "max_page_bytes": config.max_page_bytes,
            "max_output_tokens": config.max_output_tokens,
            "prompt_version": config.prompt_version,
            "processor_version": config.processor_version,
            "table_layout_version": config.table_layout_version,
        },
        "provider": None,
    }
