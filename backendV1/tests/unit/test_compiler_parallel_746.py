"""Bounded overlap and durable part coverage."""

import asyncio
from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.compilation import execution, scheduler
from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation.scheduler import run_bounded


def segment(index: int, status: str, error_code: str | None = None):
    return SimpleNamespace(segment_index=index, status=status, error_code=error_code)


def test_default_concurrency_is_one_and_existing_pins_still_apply(monkeypatch):
    limits = SimpleNamespace(COMPILER_SEGMENT_CONCURRENCY=4, MODEL_CHAT_CONCURRENCY=3)
    monkeypatch.setattr(
        "qnu.domains.modelops.document_processing.get_settings", lambda: limits
    )

    assert scheduler.effective_concurrency({}) == 1
    assert scheduler.effective_concurrency({"segmentation": {"concurrency": 2}}) == 2
    # The saved pin governs; the environment value is only a default.
    assert scheduler.effective_concurrency({"segmentation": {"concurrency": 4}}) == 4


@pytest.mark.asyncio
async def test_bounded_workers_never_exceed_the_limit():
    active = 0
    peak = 0

    async def worker(item: str) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return "completed"

    failures = await run_bounded([str(index) for index in range(7)], worker, limit=2)
    assert failures == []
    assert peak == 2


@pytest.mark.asyncio
async def test_a_failure_stops_queued_parts_but_lets_in_flight_parts_finish():
    started: list[str] = []
    finished: list[str] = []

    async def worker(item: str) -> str:
        started.append(item)
        await asyncio.sleep(0)
        if item == "0":
            raise RuntimeError("provider exploded")
        await asyncio.sleep(0.02)
        finished.append(item)
        return "completed"

    failures = await run_bounded(["0", "1", "2", "3", "4"], worker, limit=2)
    assert len(failures) == 1
    assert set(started) <= {"0", "1"}
    assert "4" not in started
    assert finished == ["1"]


@pytest.mark.asyncio
async def test_failed_status_closes_admission_before_releasing_a_slot():
    started = []

    async def worker(item):
        started.append(item)
        return "failed"

    await run_bounded(["a", "b", "c"], worker, limit=1)
    assert started == ["a"]


@pytest.mark.asyncio
async def test_cancelled_parent_drains_only_already_started_work():
    started = []
    active, release = asyncio.Event(), asyncio.Event()

    async def worker(item):
        started.append(item)
        active.set()
        await release.wait()
        return "completed"

    parent = asyncio.create_task(run_bounded(["a", "b", "c"], worker, limit=1))
    await active.wait()
    parent.cancel()
    await asyncio.sleep(0)
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await parent
    assert started == ["a"]


@pytest.mark.asyncio
async def test_failed_output_writer_does_not_drain_the_whole_queue():
    started = []
    blocked, release, writer_failed = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def worker(item):
        started.append(item)
        if item == "a":
            return "completed"
        blocked.set()
        await release.wait()
        return "completed"

    async def settled():
        await blocked.wait()
        writer_failed.set()
        raise RuntimeError("output writer failed")

    parent = asyncio.create_task(
        run_bounded(["a", "b", "c", "d"], worker, limit=1, on_settled=settled)
    )
    await writer_failed.wait()
    release.set()
    with pytest.raises(RuntimeError, match="output writer failed"):
        await parent
    assert started == ["a", "b"]


@pytest.mark.asyncio
async def test_settled_callback_runs_once_per_completion_batch():
    calls = 0

    async def worker(item: str) -> str:
        await asyncio.sleep(0.005)
        return "completed"

    async def settled() -> None:
        nonlocal calls
        calls += 1

    await run_bounded(["a", "b", "c"], worker, limit=1, on_settled=settled)
    assert calls == 3


def merge_document() -> dict:
    return {
        "ocr_run_id": "ocr_one",
        "canonical_sha256": "1" * 64,
        "manifest_sha256": "2" * 64,
        "identity": {"revision_id": "rev_one"},
        "evidence": {"ev_c1": {}},
        "pages": [
            {
                "page_number": 1,
                "status": "ready",
                "blocks": [
                    {
                        "evidence_id": "ev_c1",
                        "type": "text",
                        "text": "Nội dung nguồn.",
                        "bbox": [0, 0, 10, 10],
                    }
                ],
            }
        ],
    }


def test_parts_merge_in_source_order_not_completion_order():
    def part(heading: str, text: str) -> dict:
        return {
            "title": "Ngưỡng 2026",
            "sections": [
                {
                    "heading": heading,
                    "paragraphs": [{"text": text, "citations": ["ocr_one:ev_c1"]}],
                }
            ],
            "unknowns": [],
        }

    first, second, third = (
        part("Phần một", "Một."),
        part("Phần hai", "Hai."),
        part("Phần ba", "Ba."),
    )
    # Part 3 finished first, part 1 last.
    completed = [(3, third), (1, first), (2, second)]
    documents = [merge_document()]
    segmentation = {"state": "completed", "segments_total": 3, "segments_completed": 3}
    merged = split.merge_parts_in_order(
        completed,
        "Ngưỡng 2026",
        documents,
        "cmp_one",
        partial=False,
        segmentation=segmentation,
    )
    assert [section["heading"] for section in merged["sections"]] == [
        "Phần một",
        "Phần hai",
        "Phần ba",
    ]
    # The regression is real: the raw completion order would have merged wrongly.
    naive = split.merge_drafts(
        [payload for _, payload in completed],
        "Ngưỡng 2026",
        documents,
        "cmp_one",
        partial=False,
        segmentation=segmentation,
    )
    assert [section["heading"] for section in naive["sections"]] != [
        "Phần một",
        "Phần hai",
        "Phần ba",
    ]


@pytest.mark.asyncio
async def test_a_part_never_writes_after_its_lease_moved(monkeypatch):
    """A worker that lost the run must not touch the part or the output."""

    class FakeSession:
        async def get(self, model, key, **kwargs):
            return SimpleNamespace(worker_id="other_worker")

        async def rollback(self) -> None:
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    async def never(*args, **kwargs):
        raise AssertionError("a part without the lease must not run")

    monkeypatch.setattr(execution, "AsyncSessionFactory", lambda: FakeSession())
    monkeypatch.setattr(execution, "_run_segment", never)
    status = await execution._run_part("run_one", "worker_one", "seg_one", None, [], None, 1)
    assert status == "claim_lost"


def test_coverage_is_partial_when_any_part_is_not_completed():
    coverage = execution._coverage(
        [
            segment(1, "completed"),
            segment(2, "failed", "chat_output_truncated"),
            segment(3, "pending"),
        ]
    )
    assert coverage["state"] == "partial"
    assert coverage["segments_completed"] == 1
    assert coverage["segments_failed"] == 1
    assert coverage["segments_pending"] == 1
    assert [item["index"] for item in coverage["segments"]] == [1, 2, 3]


def test_coverage_completes_only_when_every_part_completed():
    coverage = execution._coverage(
        [segment(1, "completed"), segment(2, "received"), segment(3, "running")]
    )
    assert coverage["state"] == "partial"
    assert coverage["segments_received"] == 1
    assert coverage["segments_running"] == 1
    assert execution._coverage([segment(1, "completed")])["state"] == "completed"
