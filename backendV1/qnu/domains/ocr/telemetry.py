"""Content-free stage observations; evidence remains in the immutable artifact store."""

from __future__ import annotations

import asyncio
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Literal

from qnu.domains.ocr.errors import is_uncertain

if TYPE_CHECKING:
    from qnu.domains.ocr.models import OcrProcessingRun

Stage = Literal[
    "dispatch",
    "authorize",
    "resolve_model",
    "load_revision",
    "read_docx",
    "read_pdf",
    "render",
    "provider_preflight",
    "reserve_usage",
    "ocr_page",
    "parse_page",
    "store_artifact",
    "assemble",
    "read_artifact",
]


def run_identity(run: OcrProcessingRun) -> dict:
    """Explicit allowlist: never serialize config, requester, endpoint or credential."""
    provider = (run.config or {}).get("provider") or {}
    return {
        "trace_version": "qnu.ocr.trace/v1",
        "run_id": run.id,
        "workspace_id": run.workspace_id,
        "collection_id": run.collection_id,
        "source_id": run.source_id,
        "revision_id": run.revision_id,
        "source_sha256": run.source_sha256,
        "generation": run.generation,
        "attempt": run.attempt_count,
        "config_fingerprint": run.config_fingerprint,
        "provider_id": run.provider_id,
        "model_name": provider.get("model_name"),
        "provider_configuration_hash": provider.get("configuration_hash"),
    }


@dataclass
class StageObservation:
    status: str = "completed"
    error_code: str | None = None
    item_count: int | None = None
    byte_count: int | None = None
    sha256: str | None = None
    usage_tokens: int | None = None


@contextmanager
def observe_stage(
    run: OcrProcessingRun,
    stage: Stage,
    *,
    logger,
    page_number: int | None = None,
    artifact_kind: str | None = None,
):
    """Measure only executed work; exception details and payloads never enter logs."""
    fields = {"stage": stage}
    if page_number is not None:
        fields["page_number"] = page_number
    if artifact_kind is not None:
        fields["artifact_kind"] = artifact_kind
    observation = StageObservation()
    started = perf_counter()
    logger.info("ocr_stage_started", **run_identity(run), **fields)
    try:
        yield observation
    except BaseException as exc:
        code = getattr(exc, "code", None)
        observation.error_code = (
            code
            if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_]{1,64}", code)
            else "processing_interrupted"
            if isinstance(exc, asyncio.CancelledError)
            else "worker_lease_lost"
            if type(exc).__name__ == "LeaseLost"
            else "processing_failed"
        )
        observation.status = (
            "cancelled"
            if isinstance(exc, asyncio.CancelledError)
            else "uncertain"
            if is_uncertain(observation.error_code)
            else "failed"
        )
        raise
    finally:
        measured = {key: value for key, value in asdict(observation).items() if value is not None}
        logger.info(
            "ocr_stage_finished",
            **run_identity(run),
            **fields,
            **measured,
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
