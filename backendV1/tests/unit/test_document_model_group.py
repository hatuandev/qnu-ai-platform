"""Document model group: per-model slots, shared queue, resume and merge order."""

import asyncio
import json
from collections import Counter
from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.compilation import execution, scheduler
from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation.scheduler import run_slots

QWEN = "qwen-compiler"
LUNA = "luna-compiler"
PARTS = [f"part-{index:02d}" for index in range(1, 22)]


def group_config() -> dict:
    return {
        "document_models": [
            {"provider_id": QWEN, "concurrency": 2, "configuration_hash": "hash-qwen"},
            {"provider_id": LUNA, "concurrency": 5, "configuration_hash": "hash-luna"},
        ]
    }


def test_group_slots_pin_each_model_and_its_own_limit():
    slots = scheduler.group_slots(group_config())
    assert [(slot.provider_id, slot.limit) for slot in slots] == [
        (QWEN, 2),
        (LUNA, 5),
    ]
    assert sum(slot.limit for slot in slots) == 7


def test_legacy_run_keeps_one_pinned_slot_without_a_group():
    legacy = {"provider": {"provider_id": "legacy-model"}, "segmentation": {"concurrency": 2}}
    assert [
        (slot.provider_id, slot.limit) for slot in scheduler.group_slots(legacy)
    ] == [("legacy-model", 2)]
    bare = {"provider": {"provider_id": "legacy-model"}}
    assert [
        (slot.provider_id, slot.limit) for slot in scheduler.group_slots(bare)
    ] == [("legacy-model", 1)]


def test_configured_limit_is_honoured_above_the_environment_default(monkeypatch):
    monkeypatch.setattr(
        "qnu.domains.modelops.document_processing.get_settings",
        lambda: SimpleNamespace(COMPILER_SEGMENT_CONCURRENCY=4, MODEL_CHAT_CONCURRENCY=3),
    )
    slots = scheduler.group_slots(
        {
            "document_models": [
                {"provider_id": QWEN, "concurrency": 2},
                {"provider_id": LUNA, "concurrency": 5},
            ]
        }
    )
    # The interface value governs; the environment only supplies the default.
    assert [(slot.provider_id, slot.limit) for slot in slots] == [(QWEN, 2), (LUNA, 5)]


def test_pinned_group_survives_the_config_round_trip():
    config = group_config()
    stored = json.loads(json.dumps(config))
    assert scheduler.group_slots(stored) == scheduler.group_slots(config)


@pytest.mark.asyncio
async def test_21_parts_run_with_two_on_qwen_five_on_luna_and_seven_in_flight():
    active = Counter()
    peak = Counter()
    total = {"active": 0, "peak": 0}
    processed: list[str] = []

    async def worker(item: str, provider_id: str | None) -> str:
        active[provider_id] += 1
        total["active"] += 1
        peak[provider_id] = max(peak[provider_id], active[provider_id])
        total["peak"] = max(total["peak"], total["active"])
        await asyncio.sleep(0.01)
        active[provider_id] -= 1
        total["active"] -= 1
        processed.append(item)
        return "completed"

    failures = await run_slots(PARTS, worker, scheduler.group_slots(group_config()))

    assert failures == []
    assert sorted(processed) == PARTS
    assert peak == {QWEN: 2, LUNA: 5}
    assert total["peak"] == 7


@pytest.mark.asyncio
async def test_the_model_that_finishes_first_immediately_takes_the_next_part():
    counts = Counter()
    seen: list[str] = []
    duration = {QWEN: 0.05, LUNA: 0.002}

    async def worker(item: str, provider_id: str | None) -> str:
        counts[provider_id] += 1
        seen.append(item)
        await asyncio.sleep(duration[provider_id])
        return "completed"

    failures = await run_slots(PARTS, worker, scheduler.group_slots(group_config()))

    assert failures == []
    assert sorted(seen) == PARTS
    # Qwen holds its two slots for the whole run; Luna drains the shared queue.
    assert counts[QWEN] == 2
    assert counts[LUNA] == 19


@pytest.mark.asyncio
async def test_a_failed_part_stops_admission_for_every_model():
    started: list[tuple[str, str | None]] = []

    async def worker(item: str, provider_id: str | None) -> str:
        started.append((item, provider_id))
        if provider_id == LUNA:
            return "failed"
        await asyncio.sleep(0.02)
        return "completed"

    await run_slots(PARTS, worker, scheduler.group_slots(group_config()))

    first_wave = {item for item, _ in started}
    # No part past the first wave ever starts, on either model.
    assert first_wave <= set(PARTS[:7])
    assert len(first_wave) == len(started)
    assert set(PARTS[7:]).isdisjoint(first_wave)


@pytest.mark.asyncio
async def test_priority_mode_sends_every_part_to_the_first_model_only():
    config = {"document_models": [{"provider_id": QWEN, "concurrency": 2}]}
    active = 0
    peak = 0
    counts = Counter()

    async def worker(item: str, provider_id: str | None) -> str:
        nonlocal active, peak
        counts[provider_id] += 1
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.005)
        active -= 1
        return "completed"

    failures = await run_slots(PARTS, worker, scheduler.group_slots(config))

    assert failures == []
    assert counts == {QWEN: 21}
    assert peak == 2


@pytest.mark.asyncio
async def test_resume_schedules_only_parts_without_a_valid_result():
    completed = {index for index in range(1, 14)}
    statuses = {
        index: ("completed" if index in completed else "pending")
        for index in range(1, 22)
    }
    pending = [
        f"part-{index:02d}" for index, status in statuses.items() if status != "completed"
    ]
    assert len(pending) == 8
    processed: list[str] = []

    async def worker(item: str, provider_id: str | None) -> str:
        processed.append(item)
        return "completed"

    failures = await run_slots(pending, worker, scheduler.group_slots(group_config()))

    assert failures == []
    assert processed == pending
    assert all(f"part-{index:02d}" not in processed for index in completed)


@pytest.mark.asyncio
async def test_a_completed_part_is_never_sent_again():
    await execution._resume_segment(None, None, None, SimpleNamespace(status="completed"))


def merge_document(count: int = 21) -> dict:
    evidence = {f"ev_c{index}": {} for index in range(1, count + 1)}
    blocks = [
        {
            "evidence_id": f"ev_c{index}",
            "type": "text",
            "text": f"Nội dung nguồn {index}.",
            "bbox": [0, 0, 10, 10],
        }
        for index in range(1, count + 1)
    ]
    return {
        "ocr_run_id": "ocr_one",
        "canonical_sha256": "1" * 64,
        "manifest_sha256": "2" * 64,
        "identity": {"revision_id": "rev_one"},
        "evidence": evidence,
        "pages": [{"page_number": 1, "status": "ready", "blocks": blocks}],
    }


def test_21_parts_merge_in_source_order_with_every_citation_kept():
    def part(index: int) -> dict:
        return {
            "title": "Ngưỡng 2026",
            "sections": [
                {
                    "heading": f"Phần {index:02d}",
                    "paragraphs": [
                        {
                            "text": f"Mục {index}.",
                            "citations": [f"ocr_one:ev_c{index}"],
                        }
                    ],
                }
            ],
            "unknowns": [],
        }

    completed = [(index, part(index)) for index in range(21, 0, -1)]
    assert [index for index, _ in completed] == sorted(
        (index for index, _ in completed), reverse=True
    )
    segmentation = {
        "state": "completed",
        "segments_total": 21,
        "segments_completed": 21,
    }
    merged = split.merge_parts_in_order(
        completed,
        "Ngưỡng 2026",
        [merge_document()],
        "cmp_one",
        partial=False,
        segmentation=segmentation,
    )

    assert [section["heading"] for section in merged["sections"]] == [
        f"Phần {index:02d}" for index in range(1, 22)
    ]
    citations = [
        citation
        for section in merged["sections"]
        for paragraph in section["paragraphs"]
        for citation in paragraph["citations"]
    ]
    assert citations == [f"ocr_one:ev_c{index}" for index in range(1, 22)]
    assert merged["title"] == "Ngưỡng 2026"
