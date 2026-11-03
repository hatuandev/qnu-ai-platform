"""Versioned, pinned configuration of one OCR processing run.

Everything that can change the produced bytes is part of the fingerprint: renderer
and DPI, prompt and output limits, processor version. A run keeps its fingerprint
forever, so a later deployment cannot silently reinterpret stored evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import pymupdf

from qnu.platform.config import Settings
from qnu.platform.errors import AppException

PROCESSOR_VERSION = "qnu-ocr/v1"
PROMPT_VERSION = "nemotron-parse/v1"
CANONICAL_SCHEMA = "qnu.ocr.document/v1"
MANIFEST_SCHEMA = "qnu.ocr.manifest/v1"
MARKDOWN_VERSION = "qnu.ocr.markdown/v1"
TABLE_LAYOUT_VERSION = "nemotron-tabular/v2"

OCR_PROMPT = "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>"


def ocr_contract_hash(provider_type: str) -> str:
    if provider_type == "mineru":
        from qnu.domains.ocr.mineru_layout import VERSION

        material = f"mineru_tasks/v1|standard|auto|default|{VERSION}"
    else:
        material = OCR_PROMPT
    return hashlib.sha256(material.encode()).hexdigest()


SUPPORTED_PROCESSING_EXTENSIONS = (".pdf", ".docx")


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    """Immutable snapshot of the settings that shape the artifacts."""

    dpi: int
    max_pages: int
    max_page_bytes: int
    max_output_tokens: int | None
    prompt_version: str
    processor_version: str
    table_layout_version: str
    docx_converter: str = "docx-story"
    gotenberg_url: str = ""
    renderer_revision: str = "legacy/v1"
    pymupdf_version: str | None = None
    pin_renderer: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        values = self.as_dict()
        if not self.pin_renderer:
            # Preserve legacy/PDF identities; only DOCX requests adopt the new profile.
            for key in (
                "docx_converter",
                "gotenberg_url",
                "renderer_revision",
                "pymupdf_version",
                "pin_renderer",
            ):
                values.pop(key)
        material = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


def processing_config(settings: Settings, extension: str = ".pdf") -> ProcessingConfig:
    return ProcessingConfig(
        dpi=settings.OCR_RENDER_DPI,
        max_pages=settings.OCR_MAX_PAGES,
        max_page_bytes=settings.OCR_MAX_PAGE_BYTES,
        max_output_tokens=settings.OCR_MAX_OUTPUT_TOKENS,
        prompt_version=PROMPT_VERSION,
        processor_version=PROCESSOR_VERSION,
        table_layout_version=TABLE_LAYOUT_VERSION,
        docx_converter=settings.DOCX_CONVERTER if extension == ".docx" else "docx-story",
        gotenberg_url=(
            settings.GOTENBERG_URL.rstrip("/")
            if extension == ".docx" and settings.DOCX_CONVERTER == "gotenberg-libreoffice"
            else ""
        ),
        renderer_revision=settings.DOCX_RENDERER_REVISION if extension == ".docx" else "legacy/v1",
        pymupdf_version=pymupdf.version[0] if extension == ".docx" else None,
        pin_renderer=extension == ".docx",
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
        # Pre-v2 jobs used Story; never reinterpret them with today's Settings.
        modern = "revision" in renderer
        converter = renderer["converter"] if modern else "docx-story"
        if converter not in {"docx-story", "gotenberg-libreoffice"}:
            raise ValueError("Unsupported pinned converter")
        return ProcessingConfig(
            dpi=int(renderer["dpi"]),
            max_pages=int(renderer["max_pages"]),
            max_page_bytes=int(limits["max_page_bytes"]),
            max_output_tokens=(
                int(limits["max_output_tokens"])
                if limits["max_output_tokens"] is not None
                else None
            ),
            prompt_version=str(limits["prompt_version"]),
            processor_version=str(limits["processor_version"]),
            table_layout_version=str(limits["table_layout_version"]),
            docx_converter=converter,
            gotenberg_url=str(renderer["gotenberg_url"]) if modern else "",
            renderer_revision=str(renderer["revision"]) if modern else "legacy/v1",
            pymupdf_version=str(renderer["pymupdf_version"]) if modern else None,
            pin_renderer=modern,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AppException(
            "Cấu hình đã ghim của lượt xử lý không đọc được.",
            code="processing_config_invalid",
            status_code=409,
        ) from exc


def config_payload(config: ProcessingConfig) -> dict[str, object]:
    """Stored shape of a run config; ``provider`` is filled once a worker resolves it."""
    renderer = {"dpi": config.dpi, "max_pages": config.max_pages, "converter": "pymupdf-story"}
    if config.pin_renderer:
        renderer.update(
            {
                "converter": config.docx_converter,
                "revision": config.renderer_revision,
                "gotenberg_url": config.gotenberg_url,
                "pymupdf_version": config.pymupdf_version,
            }
        )
    return {
        "renderer": renderer,
        "ocr": {
            "max_page_bytes": config.max_page_bytes,
            "max_output_tokens": config.max_output_tokens,
            "prompt_version": config.prompt_version,
            "processor_version": config.processor_version,
            "table_layout_version": config.table_layout_version,
        },
        "provider": None,
    }
