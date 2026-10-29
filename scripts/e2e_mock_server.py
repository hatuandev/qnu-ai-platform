"""Loopback mock OpenAI-compatible server for QNU V1 E2E workflow testing.

Handles:
1. /v1/models (Discovery)
2. /v1/embeddings (1024-dim dense vectors for Qdrant indexing)
3. /v1/chat/completions (OCR parse tags, compilation, review, and assistant answers with citations)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

logger = logging.getLogger("e2e_mock_server")


class MockAiHandler(BaseHTTPRequestHandler):
    server: MockAiServer

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Quiet logs during test runs

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/v1/models", "/models"):
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": "mock-ai-model",
                            "object": "model",
                            "owned_by": "qnu-e2e",
                            "permission": [],
                        }
                    ],
                },
            )
            return
        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": f"Not found: {path}"})

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}

        if path in ("/v1/embeddings", "/embeddings"):
            self._handle_embeddings(body)
            return

        if path in ("/v1/chat/completions", "/chat/completions"):
            self._handle_chat(body)
            return

        self._send_json(404, {"error": f"Endpoint not found: {path}"})

    def _handle_embeddings(self, body: dict[str, Any]) -> None:
        inputs = body.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        model = body.get("model", "mock-ai-model")
        dim = 1024  # Standard vector size in QNU settings

        data = []
        for i, text in enumerate(inputs):
            # General token hashing for reproducible lexical overlap; not semantic quality.
            vector = [0.0] * dim
            for token in re.findall(
                r"\w+", unicodedata.normalize("NFC", str(text)).casefold()
            ):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                vector[int.from_bytes(digest[:4], "big") % dim] += (
                    1.0 if digest[4] % 2 else -1.0
                )
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vector = [value / norm for value in vector]
            data.append({"object": "embedding", "index": i, "embedding": vector})

        self._send_json(
            200,
            {
                "object": "list",
                "data": data,
                "model": model,
                "usage": {
                    "prompt_tokens": len(inputs) * 16,
                    "total_tokens": len(inputs) * 16,
                },
            },
        )

    def _handle_chat(self, body: dict[str, Any]) -> None:
        """Contract simulator only; no claim about live OCR/LLM quality."""
        messages = body.get("messages", [])
        value = messages[-1].get("content", "") if messages else ""
        try:
            incoming = json.loads(value) if isinstance(value, str) else None
        except (ValueError, TypeError):
            incoming = None
        if isinstance(value, list):
            content = "<x_0.10><y_0.10>Điểm chuẩn ngành Công nghệ thông tin năm 2024 là 24.5 điểm.<x_0.90><y_0.20><class_Text>"
        elif isinstance(incoming, dict) and "allowed_citations" in incoming:

            def texts(node):
                if isinstance(node, dict):
                    for key, item in node.items():
                        if key == "text" and isinstance(item, str) and item.strip():
                            yield item
                        elif key != "evidence":
                            yield from texts(item)
                elif isinstance(node, list):
                    for item in node:
                        yield from texts(item)

            content = json.dumps(
                {
                    "title": "Synthetic contract draft",
                    "sections": [
                        {
                            "heading": "Nội dung nguồn",
                            "paragraphs": [
                                {
                                    "text": " ".join(
                                        dict.fromkeys(texts(incoming["documents"]))
                                    )[:19000],
                                    "citations": incoming["allowed_citations"][:100],
                                }
                            ],
                        }
                    ],
                    "unknowns": [],
                },
                ensure_ascii=False,
            )
        elif (
            isinstance(incoming, dict)
            and "source_units" in incoming
            and "draft_units" in incoming
        ):
            sources, drafts = incoming["source_units"], incoming["draft_units"]
            content = json.dumps(
                {
                    "source_assessments": [
                        {
                            "source_id": s["id"],
                            "status": "covered",
                            "draft_ids": [drafts[0]["id"]],
                            "explanation": "Synthetic contract assessment; not a quality evaluation.",
                            "suggested_action": "",
                        }
                        for s in sources
                    ],
                    "draft_assessments": [
                        {
                            "draft_id": d["id"],
                            "status": "supported",
                            "source_ids": [s["id"] for s in sources],
                            "explanation": "Synthetic contract assessment.",
                            "suggested_action": "",
                        }
                        for d in drafts
                    ],
                },
                ensure_ascii=False,
            )
        elif isinstance(incoming, dict) and "evidence" in incoming:
            evidence = incoming["evidence"]
            content = json.dumps(
                {
                    "status": "answered" if evidence else "insufficient_evidence",
                    "statements": [
                        {
                            "text": re.sub(
                                r"\[[^\]]*\]|<[^>]*>", " ", evidence[0]["text"]
                            )[:11000],
                            "evidence_ids": [evidence[0]["evidence_id"]],
                        }
                    ]
                    if evidence
                    else [],
                },
                ensure_ascii=False,
            )
        elif isinstance(incoming, dict) and "units" in incoming:
            content = json.dumps({"suggestions": []})
        else:
            self._send_json(
                400, {"error": {"message": "Unsupported synthetic model contract"}}
            )
            return
        self._send_json(
            200,
            {
                "id": "e2e-contract",
                "object": "chat.completion",
                "model": body.get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 100,
                    "total_tokens": 200,
                },
            },
        )


class MockAiServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.server = ThreadingHTTPServer((host, port), MockAiHandler)
        self.server.daemon_threads = True
        self.host, self.port = self.server.server_address[:2]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


if __name__ == "__main__":
    import time

    s = MockAiServer(port=20188)
    s.start()
    print(f"Mock AI server running at {s.base_url}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        s.stop()
