"""Helpers for OCR acceptance tests: real PDF/DOCX bytes and a loopback Nemotron.

The provider is a real HTTP server on 127.0.0.1, so the adapter exercises the same
endpoint resolution, auth header, timeout and JSON handling as production. It is a
*mock provider*, not a live Nemotron run: live OCR needs a real endpoint and is
reported separately as NOT RUN.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pymupdf
from fastapi.testclient import TestClient

from qnu.api.dependencies import get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.ocr.config import OCR_PROMPT
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from tests.docx_fixture import docx_with_table  # noqa: F401 -- shared fixture re-export
from tests.integration.knowledge_support import (
    API,
    PLATFORM,
    active_actor,
    as_actor,
    create_collection,
    upload_source,
)


# --------------------------------------------------------------------------- documents
def real_pdf(pages: list[str | None]) -> bytes:
    """Valid PDF with one text page per entry; ``None`` renders a truly blank page."""
    document = pymupdf.open()
    try:
        for text in pages:
            page = document.new_page(width=595, height=842)
            if text:
                page.insert_textbox(pymupdf.Rect(50, 60, 545, 790), text, fontsize=11)
        return document.tobytes()
    finally:
        document.close()


def ocr_blocks(*blocks: str) -> str:
    """Build a Nemotron-style located response from (text, class) pairs."""
    parts = []
    for index, block in enumerate(blocks):
        text, label = block.split("|", 1)
        top = 0.05 + index * 0.12
        parts.append(f"<x_0.10><y_{top:.2f}>{text}<x_0.90><y_{top + 0.08:.2f}><class_{label}>")
    return "".join(parts)


TABLE_RESPONSE = ocr_blocks(
    "PHỤ LỤC 01|Title",
    (
        "\\begin{tabular}{cccc} \\hline \\thead{STT} & \\thead{Chỉ tiêu} & "
        "\\thead{Năm 2023} & \\thead{Năm 2024} \\\\ "
        "1 & Chỉ tiêu tuyển sinh & 0 & - \\\\ "
        "2 & Chỉ tiêu trúng tuyển & & 150 \\\\ \\end{tabular}"
        "|Table"
    ),
    "Ghi chú: số liệu năm 2023.|Footnote",
)


# --------------------------------------------------------------------------- provider
class FakeNemotron:
    """Loopback OpenAI-compatible OCR endpoint with switchable failure modes."""

    def __init__(self) -> None:
        self.mode = "ok"
        self.delay_seconds = 0.0
        self.responses: list[str] = []
        self.requests: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def content_for(self, index: int) -> str:
        if index < len(self.responses):
            return self.responses[index]
        return ocr_blocks(f"Trang {index + 1}|Text")

    def _respond(self, index: int) -> tuple[int, bytes]:
        if self.mode == "http_error":
            return 500, b'{"error":"boom"}'
        if self.mode == "malformed":
            return 200, json.dumps({"choices": []}).encode()
        if self.mode == "truncated":
            payload = {
                "choices": [
                    {"message": {"content": self.content_for(index)}, "finish_reason": "length"}
                ]
            }
            return 200, json.dumps(payload).encode()
        if self.mode == "empty":
            payload = {"choices": [{"message": {"content": "   "}, "finish_reason": "stop"}]}
            return 200, json.dumps(payload).encode()
        if self.mode == "invalid_layout":
            payload = {
                "choices": [{"message": {"content": "không có khối"}, "finish_reason": "stop"}]
            }
            return 200, json.dumps(payload).encode()
        payload = {
            "id": "chatcmpl-test",
            "model": "nemotron-parse",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": self.content_for(index)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140},
        }
        return 200, json.dumps(payload).encode()

    def _handler(self):
        owner = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw)
                except ValueError:
                    body = {}
                # Concurrent callers may overlap: pin this request's index while
                # appending so `_respond(index)` always reads its own body.
                with owner._lock:
                    owner.requests.append(
                        {
                            "path": self.path,
                            "authorization": self.headers.get("Authorization"),
                            "content_type": self.headers.get("Content-Type"),
                            "body": body,
                        }
                    )
                    index = len(owner.requests) - 1
                if owner.delay_seconds:
                    time.sleep(owner.delay_seconds)
                status, payload = owner._respond(index)
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    # The client timed out mid-response; the timeout is the result we want.
                    pass

            def log_message(self, *args: object) -> None:
                pass

        return _Handler

    def __enter__(self) -> FakeNemotron:  # noqa: PYI034
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()


# --------------------------------------------------------------------------- setup
class FakeJobQueue:
    """In-memory queue: records jobs and de-duplicates by job id, like ARQ."""

    def __init__(self, *, failing: bool = False) -> None:
        self.failing = failing
        self.jobs: list[dict[str, Any]] = []

    async def enqueue(self, function: str, *args: object, job_id: str | None = None) -> bool:
        if self.failing:
            raise OSError("redis is unavailable")
        if job_id and any(job["job_id"] == job_id for job in self.jobs):
            return False
        self.jobs.append({"function": function, "args": args, "job_id": job_id})
        return True


def use_queue(queue: FakeJobQueue | None) -> None:
    app.dependency_overrides[get_job_queue] = lambda: queue


def setup_ocr_provider(
    client: TestClient,
    workspace_id: str,
    base_url: str,
    *,
    capabilities: tuple[str, ...] = ("ocr",),
    secret: str | None = "nemotron-test-secret",
    timeout_seconds: int = 5,
    activate: bool = True,
    model_name: str = "nemotron-parse",
    quota: int | None = 1_000_000,
) -> dict[str, Any]:
    caller = active_actor()
    as_actor(PLATFORM)
    created = client.post(
        f"{API}/modelops/providers",
        json={
            "name": f"nemotron-{abs(hash((workspace_id, base_url))) % 100000}",
            "provider_type": "openai_compatible",
            "base_url": base_url,
            "model_name": model_name,
            "capabilities": list(capabilities),
            "timeout_seconds": timeout_seconds,
            "token_limits": {
                "context_window_tokens": 262144,
                "max_output_tokens": 131072,
                "ocr_page_input": {
                    "max_image_width": 4096,
                    "max_image_height": 4096,
                    "input_tokens_upper_bound": 8192,
                    "prompt_sha256": hashlib.sha256(OCR_PROMPT.encode()).hexdigest(),
                },
            },
        },
    )
    assert created.status_code == 201, created.text
    provider = created.json()
    if secret is not None:
        key = client.post(
            f"{API}/modelops/providers/{provider['id']}/keys",
            json={"name": "ocr-key", "secret": secret},
        )
        assert key.status_code == 201, key.text
    granted = client.put(
        f"{API}/workspaces/{workspace_id}/allowed-providers",
        json={"provider_ids": [provider["id"]], "defaults": {"ocr": provider["id"]}},
    )
    assert granted.status_code == 200, granted.text
    if quota is not None:
        # A workspace without a quota row cannot reserve tokens at all, so the
        # ordinary flow needs a budget; the quota test passes 0 explicitly.
        set_quota(client, workspace_id, quota)
        as_actor(PLATFORM)
    if not activate:
        # Deactivate only after the grant: a disabled provider cannot be granted.
        patched = client.patch(
            f"{API}/modelops/providers/{provider['id']}", json={"is_active": False}
        )
        assert patched.status_code == 200, patched.text
    as_actor(caller)
    return provider


def set_quota(client: TestClient, workspace_id: str, limit: int | None, blocked: bool = False):
    caller = active_actor()
    as_actor(PLATFORM)
    response = client.put(
        f"{API}/workspaces/{workspace_id}/quota",
        json={"monthly_token_limit": limit, "is_blocked": blocked},
    )
    as_actor(caller)
    return response


def prepare_source(
    client: TestClient,
    workspace_id: str,
    collection_name: str,
    *,
    payload: bytes | None = None,
    filename: str = "phu-luc-01.pdf",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Create a collection and upload one source; returns (collection, source, revision)."""
    collection = create_collection(client, workspace_id, collection_name)
    response = upload_source(
        client,
        workspace_id,
        collection["id"],
        payload=payload if payload is not None else real_pdf(["PHU LUC 01"]),
        filename=filename,
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if filename.endswith(".docx")
            else "text/plain; charset=utf-8"
            if filename.endswith((".txt", ".md"))
            else "application/pdf"
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return collection, body["source"], body["revision"]


def runs_url(workspace_id: str, collection_id: str, source_id: str, revision_id: str) -> str:
    return (
        f"{API}/workspaces/{workspace_id}/collections/{collection_id}"
        f"/sources/{source_id}/revisions/{revision_id}/processing-runs"
    )


def request_run(
    client: TestClient,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    *,
    provider_id: str | None = None,
    queue: FakeJobQueue | None = None,
    body: dict[str, Any] | None = None,
):
    use_queue(queue)
    payload: dict[str, Any] = dict(body or {})
    if provider_id:
        payload["provider_id"] = provider_id
    return client.post(runs_url(workspace_id, collection_id, source_id, revision_id), json=payload)


def execute_now(client: TestClient, run_id: str, *, engine: object | None = None):
    """Run the worker body in the application loop, against the real container."""
    from qnu.domains.ocr.execution import execute_run

    container = app.state.container
    chosen = engine if engine is not None else container.ocr_engine

    async def _run():
        async with AsyncSessionFactory() as session:
            return await execute_run(
                session,
                container.blob_store,
                run_id,
                worker_id="test-worker",
                engine=chosen,
                job_queue=None,
            )

    return client.portal.call(_run)


def actor_editor(actor: AuthActor) -> None:
    as_actor(actor)
