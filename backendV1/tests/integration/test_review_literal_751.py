"""Exact table retention uses local checks while narrative keeps model review."""

import threading
import time

from sqlalchemy import select

from qnu.domains.knowledge.compilation.review.models import CompilationReviewSegment
from qnu.platform.database import AsyncSessionFactory
from tests.integration import compiler_support
from tests.integration.compiler_support import chat_provider, execute_compile, request_compile
from tests.integration.ocr_support import ocr_blocks, set_quota
from tests.integration.test_compiler_review_segments_750 import (
    SegmentedReviewChat,
    small_provider,
)


class OverlapChat(SegmentedReviewChat):
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()
        self.active = self.peak = 0

    def _respond(self, index):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(1)
            return super()._respond(index)
        finally:
            with self.lock:
                self.active -= 1


def test_literal_table_parts_are_durable_and_do_not_dispatch_chat(client, monkeypatch):
    rows = " ".join(f"{index} & Ngành {index} & 2026 & {index + 10} \\\\" for index in range(1, 41))
    table = "\\begin{tabular}{cccc} STT & Ngành & Năm & Ngưỡng \\\\" + rows + "\\end{tabular}"
    monkeypatch.setattr(
        compiler_support,
        "TABLE_RESPONSE",
        ocr_blocks(
            "Điều kiện năm 2026|Title",
            table + "|Table",
            "Ghi chú điều kiện giữ nguyên.|Footnote",
        ),
    )
    data = compiler_support.processed_input(client, code="literal-review751")
    with OverlapChat() as chat:
        provider = chat_provider(client, data, chat.base_url, model="large-chat")
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        requested = request_compile(client, data)
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        small = small_provider(
            client,
            {**data, "provider": provider},
            chat.base_url,
            context_window=40960,
            max_output=4096,
        )
        base = data["url"] + "/" + run_id + "/reviews"
        before = len(chat.requests)
        chat.peak = 0
        response = client.post(
            base,
            json={"provider_id": small["id"]},
            headers={"Idempotency-Key": "literal-review751"},
        )
        assert response.status_code == 200, response.text
        review = response.json()
        assert review["status"] == "completed", review

        async def rows_saved():
            async with AsyncSessionFactory() as db:
                return list(
                    (
                        await db.scalars(
                            select(CompilationReviewSegment).where(
                                CompilationReviewSegment.review_id == review["id"],
                            )
                        )
                    ).all()
                )

        saved = client.portal.call(rows_saved)
        local = [
            row for row in saved if row.config.get("assessment_method") == "literal_equality/v1"
        ]
        assert local
        assert all(row.usage_tokens == 0 and row.request_started_at is None for row in local)
        assert len(chat.requests) - before == len(saved) - len(local)
        assert chat.peak == 2
        assert all(row.status == "completed" for row in saved)
        content = client.get(f"{base}/{review['id']}/report").json()
        assert content["summary"]["source_units_checked"] == 166
        assert content["summary"]["draft_units_checked"] >= 164
        sent = len(chat.requests)
        assert (
            client.post(
                base,
                json={"provider_id": small["id"]},
                headers={"Idempotency-Key": "literal-review751"},
            ).status_code
            == 200
        )
        assert len(chat.requests) == sent
