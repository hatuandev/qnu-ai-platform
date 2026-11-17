"""21 independent parts run through the real executor across two pinned group models.

Two loopback HTTP providers stand in for Qwen (2 slots) and Luna (5 slots): the
adapter, scheduling, persistence and merge are the production ones, only the model
endpoints are fake. This proves concurrency, immediate pickup by the faster model,
in-order merge and per-part model pinning; it says nothing about real provider
latency or capacity. Skipped (NOT RUN) without ``TEST_DATABASE_URL``.
"""

from __future__ import annotations

import json
import os
import threading
import time

import pytest
from sqlalchemy import select

if not os.environ.get("TEST_DATABASE_URL", "").strip():
    pytest.skip(
        "NOT RUN: TEST_DATABASE_URL chưa cấu hình (Postgres test riêng).",
        allow_module_level=True,
    )

from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation.models import CompilationSegment
from qnu.platform.database import AsyncSessionFactory
from tests.integration.compiler_support import (
    FakeChat,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor

PARTS = 21
# Long enough that slot occupancy overlaps despite per-part startup skew.
QWEN_DELAY = 0.9
LUNA_DELAY = 0.4


def located_blocks(count: int) -> str:
    """One located text block per line, all inside the page bounds."""
    step = 0.92 / count
    return "".join(
        f"<x_0.10><y_{0.02 + index * step:.3f}>Đoạn {index + 1}"
        f"<x_0.90><y_{0.02 + index * step + 0.03:.3f}><class_Text>"
        for index in range(count)
    )


class Meter:
    """In-flight calls per loopback endpoint, measured server-side."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total = 0
        self.total_peak = 0
        self.calls: dict[str, int] = {}
        self.in_flight: dict[str, int] = {}
        self.peaks: dict[str, int] = {}
        self.citation_by_part: dict[int, str] = {}

    def enter(self, name: str) -> None:
        with self._lock:
            self.total += 1
            self.total_peak = max(self.total_peak, self.total)
            self.calls[name] = self.calls.get(name, 0) + 1
            self.in_flight[name] = self.in_flight.get(name, 0) + 1
            self.peaks[name] = max(self.peaks.get(name, 0), self.in_flight[name])

    def leave(self, name: str) -> None:
        with self._lock:
            self.total -= 1
            self.in_flight[name] -= 1

    def record(self, part_index: int, citation: str) -> None:
        with self._lock:
            self.citation_by_part[part_index] = citation


class MeteredChat(FakeChat):
    """One fake group model: same request contract, its own latency and counters."""

    def __init__(self, meter: Meter, name: str, delay: float) -> None:
        super().__init__()
        self.meter, self.name, self.delay = meter, name, delay

    def _respond(self, index: int):
        self.meter.enter(self.name)
        try:
            time.sleep(self.delay)
            incoming = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
            owned = incoming["part"]["owned"][0]
            citation = f"{owned['ocr_run_id']}:{owned['evidence_id']}"
            assert citation in incoming["allowed_citations"], citation
            part = incoming["part"]["index"]
            self.meter.record(part, citation)
            draft = {
                "title": "Chỉ tiêu tuyển sinh",
                "sections": [
                    {
                        "heading": "Nguồn dữ liệu",
                        "paragraphs": [
                            {"text": f"Phần {part} từ {citation}.", "citations": [citation]}
                        ],
                    }
                ],
                "unknowns": [],
            }
            body = {
                "model": self.name,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(draft, ensure_ascii=False),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 123, "completion_tokens": 50, "total_tokens": 173},
            }
            self.last_raw = json.dumps(body, ensure_ascii=False).encode()
            return 200, self.last_raw
        finally:
            self.meter.leave(self.name)


def chat_endpoint(client, name: str, base_url: str) -> dict:
    as_actor(PLATFORM)
    created = client.post(
        f"{API}/modelops/providers",
        json={
            "name": name,
            "provider_type": "openai_compatible",
            "base_url": base_url,
            "model_name": "test-chat",
            "capabilities": ["chat"],
            "timeout_seconds": 30,
            "token_limits": {"context_window_tokens": 131072, "max_output_tokens": 8192},
        },
    )
    assert created.status_code == 201, created.text
    provider = created.json()
    key = client.post(
        f"{API}/modelops/providers/{provider['id']}/keys",
        json={"name": "chat-key", "secret": f"group-e2e-{name}"},
    )
    assert key.status_code == 201, key.text
    return provider


def one_part_per_block(documents, topic, *, capacity, structured, **options):
    """Force exactly PARTS parts, one real unit each, without touching content."""
    units = split.build_units(documents)
    assert len(units) == PARTS, [(unit.page_number, unit.evidence_id) for unit in units]
    return [
        split.build_plan(
            index=index + 1,
            units=[unit],
            documents=documents,
            topic=topic,
            structured=structured,
            total_estimate=len(units),
        )
        for index, unit in enumerate(units)
    ]


def test_21_parts_run_across_two_pinned_models_and_merge_in_source_order(
    client, monkeypatch
):
    data = processed_input(
        client, code="group-21-parts", response=located_blocks(PARTS)
    )
    meter = Meter()
    with MeteredChat(meter, "qwen", QWEN_DELAY) as qwen, MeteredChat(
        meter, "luna", LUNA_DELAY
    ) as luna:
        qwen_provider = chat_endpoint(client, f"qwen-{data['workspace']['id']}", qwen.base_url)
        luna_provider = chat_endpoint(client, f"luna-{data['workspace']['id']}", luna.base_url)
        as_actor(PLATFORM)
        defaults = client.put(
            f"{API}/modelops/defaults",
            json={
                "ocr_provider_id": data["ocr_provider"]["id"],
                "chat_provider_id": qwen_provider["id"],
            },
        )
        assert defaults.status_code == 200, defaults.text
        saved = client.patch(
            f"{API}/modelops/document-processing",
            json={
                "mode": "parallel",
                "models": [
                    {"provider_id": qwen_provider["id"], "concurrency": 2},
                    {"provider_id": luna_provider["id"], "concurrency": 5},
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        as_actor(EDITOR)

        # The saved group limit (7 total) governs even if the local .env default is lower.
        monkeypatch.setattr(split, "plan_segments", one_part_per_block)
        created = request_compile(
            client, data, key="group-21-parts", topic="Chỉ tiêu tuyển sinh"
        )
        assert created.status_code == 201, created.text
        run_id = created.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"

        # Slots respected; the fast model kept taking parts as it freed a slot.
        assert meter.peaks["qwen"] <= 2
        assert meter.peaks["luna"] <= 5
        assert meter.total_peak <= 7
        assert meter.total_peak == 7, (meter.peaks, meter.total_peak, meter.calls)
        assert meter.calls["qwen"] + meter.calls["luna"] == PARTS
        assert meter.calls["luna"] > PARTS // 2, meter.calls
        assert meter.calls["qwen"] >= 1

        base = f"{data['url']}/{run_id}"
        progress = client.get(base + "/progress")
        assert progress.status_code == 200, progress.text
        body = progress.json()
        assert body["status"] == "completed"
        assert body["total"] == PARTS and body["completed"] == PARTS
        assert body["concurrency"] == 7
        assert body["running"] == 0 and body["pending"] == 0
        assert len(body["segments"]) == PARTS

        async def segment_pins():
            async with AsyncSessionFactory() as session:
                rows = await session.scalars(
                    select(CompilationSegment)
                    .where(CompilationSegment.run_id == run_id)
                    .order_by(CompilationSegment.segment_index)
                )
                return [
                    (
                        row.segment_index,
                        row.status,
                        row.config.get("assigned_provider_id"),
                    )
                    for row in rows
                ]

        pins = client.portal.call(segment_pins)
        assert [index for index, _, _ in pins] == list(range(1, PARTS + 1))
        assert all(status == "completed" for _, status, _ in pins)
        assigned = [provider_id for _, _, provider_id in pins]
        assert assigned.count(qwen_provider["id"]) == meter.calls["qwen"]
        assert assigned.count(luna_provider["id"]) == meter.calls["luna"]
        assert set(assigned) == {qwen_provider["id"], luna_provider["id"]}

        draft = client.get(base + "/draft").json()
        paragraphs = [
            paragraph
            for section in draft["sections"]
            for paragraph in section["paragraphs"]
        ]
        expected = [
            f"Phần {index} từ {meter.citation_by_part[index]}." for index in range(1, PARTS + 1)
        ]
        assert [paragraph["text"] for paragraph in paragraphs] == expected
        citations = [paragraph["citations"][0] for paragraph in paragraphs]
        assert len(set(citations)) == PARTS
        assert citations == sorted(citations)

        # A finished run cannot be executed again: no part is resent.
        calls_before = dict(meter.calls)
        assert execute_compile(client, run_id) == "not_claimed"
        assert meter.calls == calls_before
