"""MinerU task API. One document submission; resume only by the durable task ID."""

import asyncio
import hashlib
import re
import time

import httpx

from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.ocr_engine import (
    DocumentCheckpoint,
    DocumentGuard,
    OcrDocumentRequest,
    OcrDocumentResponse,
)

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_CONTROL_BYTES = 1024 * 1024


def api_url(endpoint: str) -> str:
    base = endpoint.rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def error(code: str, *, uncertain: bool = False) -> AppException:
    return AppException(
        "Tác vụ MinerU chưa có kết quả hợp lệ; giữ mã tác vụ, không tự gửi lại PDF.",
        code="ocr_provider_timeout" if uncertain else code,
        status_code=504 if uncertain else 502,
    )


def task_ids(data: dict) -> tuple[str, str]:
    try:
        task, file = data["task_id"], data["files"][0]["file_id"]
        if not all(
            isinstance(x, str) and re.fullmatch(r"[\w-]{1,128}", x, re.ASCII) for x in (task, file)
        ):
            raise ValueError
        return task, file
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise error("mineru_response_invalid") from exc


class MineruOcrEngine:
    name = "mineru"

    def __init__(self, *, transport=None, poll_seconds: float = 2):
        self.transport, self.poll_seconds = transport, poll_seconds

    async def extract_document(
        self,
        pdf: bytes,
        request: OcrDocumentRequest,
        *,
        checkpoint: dict,
        save: DocumentCheckpoint,
        guard: DocumentGuard,
    ) -> OcrDocumentResponse:
        base = api_url(request.endpoint)
        assert_allowed_endpoint(base, allow_private=not get_settings().is_production)
        if not pdf.startswith(b"%PDF"):
            raise error("mineru_pdf_required")
        if not request.api_key and not request.auth_optional:
            raise error("ocr_credentials_missing")
        headers = {"Authorization": f"Bearer {request.api_key}"} if request.api_key else {}
        started = time.monotonic()
        state = dict(checkpoint)
        checksum = hashlib.sha256(pdf).hexdigest()
        if state and state.get("input_sha256") != checksum:
            raise error("mineru_checkpoint_mismatch")
        if state and state.get("ocr_mode", "auto") != request.ocr_mode:
            raise error("mineru_checkpoint_mismatch")
        state["ocr_mode"] = request.ocr_mode
        timeout = httpx.Timeout(request.timeout_seconds, connect=min(10, request.timeout_seconds))
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                async with asyncio.timeout(
                    None if request.wait_for_completion else request.timeout_seconds
                ):
                    await guard()
                    task, file = await self._submit(client, base, pdf, state, checksum, save, guard)
                    await self._poll(client, base, task, file, guard)
                    await guard()
                    archive = await self._read(
                        client, "GET", f"{base}/files/{file}/content", limit=MAX_ARCHIVE_BYTES
                    )
                    return OcrDocumentResponse(archive, int((time.monotonic() - started) * 1000))
        except (TimeoutError, httpx.RequestError) as exc:
            raise error("mineru_transport_uncertain", uncertain=True) from exc

    async def _submit(self, client, base, pdf, state, checksum, save, guard):
        if "task_id" not in state:
            if state.get("phase"):
                raise error("mineru_submission_uncertain", uncertain=True)
            state.update(input_sha256=checksum, phase="creating")
            await save(dict(state))
            raw = await self._read(
                client,
                "POST",
                base + "/tasks",
                expected=202,
                json={
                    "files": [
                        {"file_name": "document.pdf", "bytes": len(pdf), "sha256sum": checksum}
                    ],
                    "tier": "standard",
                    "ocr_mode": state["ocr_mode"],
                    "output_formats": ["default"],
                },
            )
            data = self._json(raw)
            task, file = task_ids(data)
            state.update(task_id=task, file_id=file, phase="created")
            await save(dict(state))
        task, file = task_ids(
            {"task_id": state["task_id"], "files": [{"file_id": state.get("file_id")}]}
        )
        if state["phase"] == "created":
            await guard()
            state["phase"] = "uploading"
            await save(dict(state))
            await self._read(
                client,
                "PUT",
                f"{base}/tasks/{task}/uploads/{file}",
                content=pdf,
                headers={"Content-Type": "application/octet-stream"},
            )
            state["phase"] = "uploaded"
            await save(dict(state))
        # An interrupted PUT may already have started parsing. Never upload again.
        return task, file

    async def _poll(self, client, base, task, file, guard):
        while True:
            await guard()
            data = self._json(await self._read(client, "GET", f"{base}/tasks/{task}"))
            if data.get("task_id") != task:
                raise error("mineru_response_invalid")
            files = data.get("files")
            if (
                not isinstance(files, list)
                or len(files) != 1
                or not isinstance(files[0], dict)
                or files[0].get("file_id") != file
            ):
                raise error("mineru_response_invalid")
            if data.get("status") == "completed":
                if files[0].get("status") != "completed":
                    raise error("mineru_response_incomplete")
                return
            if data.get("status") not in {
                "queued",
                "pending",
                "running",
                "processing",
                "uploading",
                "created",
                "waiting_upload",
                "waiting-file",
                "uploaded",
            }:
                raise error("mineru_task_failed")
            await asyncio.sleep(self.poll_seconds)

    @staticmethod
    def _json(raw):
        import json

        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise TypeError
            return data
        except (ValueError, TypeError) as exc:
            raise error("mineru_response_invalid") from exc

    @staticmethod
    async def _read(client, method, url, *, limit=MAX_CONTROL_BYTES, expected=200, **kwargs):
        async with client.stream(method, url, **kwargs) as response:
            if response.status_code != expected:
                code = (
                    "ocr_provider_auth_failed"
                    if response.status_code in (401, 403)
                    else "mineru_http_error"
                )
                raise error(code)
            chunks, size = [], 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > limit:
                    raise error("mineru_response_too_large")
                chunks.append(chunk)
            return b"".join(chunks)
