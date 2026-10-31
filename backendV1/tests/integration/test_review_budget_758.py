"""Independent checks of review ceilings through real HTTP and PostgreSQL sessions."""

import json
from dataclasses import replace

import pytest

from qnu.domains.knowledge.compilation.review import refinement
from tests.integration.compiler_support import (
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.ocr_support import set_quota
from tests.integration.test_compiler_review_segments_750 import (
    SegmentedReviewChat,
    small_provider,
)


@pytest.mark.parametrize("ceiling", ["requests", "tokens"])
def test_parallel_review_obeys_one_request_ceiling(client, monkeypatch, ceiling):
    data = processed_input(client, code=f"review-budget-758-{ceiling}")
    with SegmentedReviewChat() as chat:
        provider = chat_provider(client, data, chat.base_url, model="big-chat")
        assert set_quota(client, data["workspace"]["id"], 5_000_000).status_code == 200
        requested = request_compile(client, data)
        assert requested.status_code == 201, requested.text
        run_id = requested.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        small = small_provider(
            client,
            {**data, "provider": provider},
            chat.base_url,
            context_window=40960,
            max_output=4096,
        )
        original_limits = refinement.limits_for

        def strict_limits(*args, **kwargs):
            limits = original_limits(*args, **kwargs)
            if ceiling == "requests":
                return replace(limits, max_requests=1)
            return replace(limits, max_tokens=1)

        monkeypatch.setattr(refinement, "limits_for", strict_limits)
        response = client.post(
            data["url"] + "/" + run_id + "/reviews",
            json={"provider_id": small["id"]},
            headers={"Idempotency-Key": f"review-budget-758-{ceiling}"},
        )
        assert response.status_code == 422, response.text
        assert response.json()["code"] == f"compilation_review_budget_{ceiling}_exceeded"
        reviews_sent = [
            request
            for request in chat.requests
            if "source_units" in json.loads(request["body"]["messages"][-1]["content"])
        ]
        assert len(reviews_sent) == (1 if ceiling == "requests" else 0)

        if ceiling == "requests":
            # Replaying the same key probes the stop guard, never another model attempt.
            from sqlalchemy import select

            from qnu.domains.knowledge.compilation.review.models import CompilationReview
            from qnu.platform.database import AsyncSessionFactory

            async def exhausted_time():
                async with AsyncSessionFactory() as db:
                    row = (
                        await db.scalars(
                            select(CompilationReview).where(
                                CompilationReview.compilation_run_id == run_id,
                            )
                        )
                    ).one()
                    trace = dict(row.trace)
                    trace["execution_elapsed_seconds"] = 65.0
                    trace["refinement_policy"] = {"max_seconds": 60, "max_requests": 1}
                    row.trace = trace
                    await db.commit()
                    return row.trace["execution_token"]

            token = client.portal.call(exhausted_time)
            calls_before_replay = len(chat.requests)
            again = client.post(
                data["url"] + "/" + run_id + "/reviews",
                json={"provider_id": small["id"]},
                headers={"Idempotency-Key": "review-budget-758-requests"},
            )
            assert again.status_code == 422, again.text
            assert again.json()["code"] == "compilation_review_budget_time_exceeded"
            assert len(chat.requests) == calls_before_replay

            async def current_token():
                async with AsyncSessionFactory() as db:
                    row = (
                        await db.scalars(
                            select(CompilationReview).where(
                                CompilationReview.compilation_run_id == run_id,
                            )
                        )
                    ).one()
                    assert row.status == "failed"
                    return row.trace["execution_token"]

            assert client.portal.call(current_token) == token
