"""Regression coverage for saved DOCX render reuse; no live converter required."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.ocr import execution
from qnu.domains.ocr.config import processing_config
from qnu.platform.config import Settings
from qnu.platform.errors import AppException


@pytest.mark.asyncio
async def test_saved_conversion_is_used_without_contacting_converter(monkeypatch):
    config = processing_config(Settings(_env_file=None), ".docx")
    renderer = {"name": "gotenberg", "converter": "gotenberg-libreoffice"}
    run = SimpleNamespace(
        id="run",
        config={
            "render_result": {
                "renderer": renderer,
                "warnings": ["pinned-warning"],
            }
        },
    )
    monkeypatch.setattr(execution, "_artifact", AsyncMock(return_value=object()))
    read = AsyncMock(return_value=(object(), b"saved-pdf"))
    cached_render = AsyncMock(return_value="saved-render")
    convert = AsyncMock(side_effect=AssertionError("Must not reconvert"))
    monkeypatch.setattr(execution, "read_artifact_bytes", read)
    monkeypatch.setattr(execution, "render_saved_pdf_async", cached_render)
    monkeypatch.setattr(execution, "render_async", convert)
    assert (
        await execution._render_for_run(
            None,
            None,
            run,
            b"original-docx",
            ".docx",
            config,
        )
        == "saved-render"
    )
    read.assert_awaited_once_with(None, None, run, "render_pdf", 0)
    cached_render.assert_awaited_once_with(b"saved-pdf", config, renderer, ("pinned-warning",))
    convert.assert_not_awaited()


@pytest.mark.asyncio
async def test_corrupt_saved_render_never_falls_back_to_reconversion(monkeypatch):
    config = processing_config(Settings(_env_file=None), ".docx")
    run = SimpleNamespace(id="run", config={})
    monkeypatch.setattr(execution, "_artifact", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        execution,
        "read_artifact_bytes",
        AsyncMock(
            side_effect=AppException(
                "Artifact hash mismatch",
                code="artifact_integrity_failed",
                status_code=502,
            )
        ),
    )
    convert = AsyncMock()
    monkeypatch.setattr(execution, "render_async", convert)
    with pytest.raises(AppException, match="Artifact hash mismatch"):
        await execution._render_for_run(None, None, run, b"docx", ".docx", config)
    convert.assert_not_awaited()
