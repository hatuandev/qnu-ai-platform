"""Skip acknowledgements cannot move to another version, metadata or compilation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.knowledge.publication.review_gate import acknowledge_skip, recheck
from qnu.domains.knowledge.publication.schemas import PreviewRequest, ReviewSkipAcknowledgement
from qnu.platform.errors import Conflict


def target():
    return SimpleNamespace(
        id="version",
        compilation_run_id="compiler",
        bundle_sha256="a" * 64,
        retrieval_metadata=[{"synthetic": "metadata"}],
    )


def acknowledgement(t):
    return ReviewSkipAcknowledgement(
        confirmed_skip=True,
        version_id=t.id,
        bundle_sha256=t.bundle_sha256,
        retrieval_metadata_sha256=digest(t.retrieval_metadata),
    )


def test_skip_requires_exact_metadata_hash():
    t = target()
    ack = acknowledgement(t).model_copy(update={"retrieval_metadata_sha256": None})
    with pytest.raises(Conflict, match="metadata"):
        acknowledge_skip(t, ack, "User explicitly skips AI review.")


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "another"),
        ("bundle_sha256", "b" * 64),
        ("retrieval_metadata", [{"different": "metadata"}]),
    ],
)
def test_skip_is_not_reusable_after_target_changes(field, value):
    t = target()
    ack = acknowledgement(t)
    setattr(t, field, value)
    with pytest.raises(Conflict):
        acknowledge_skip(t, ack, "User explicitly skips AI review.")


@pytest.mark.asyncio
async def test_recheck_does_not_fabricate_a_review_and_rejects_wrong_compiler():
    t = target()
    saved = acknowledge_skip(t, acknowledgement(t), "User explicitly skips AI review.")
    db, blob = AsyncMock(), AsyncMock()
    await recheck(db, blob, t, saved)
    db.execute.assert_not_called()
    saved["compilation_run_id"] = "another"
    with pytest.raises(Conflict):
        await recheck(db, blob, t, saved)


def test_request_cannot_claim_review_and_skip_at_the_same_time():
    t = target()
    with pytest.raises(ValueError):
        PreviewRequest(
            action="approve",
            reason="Explicit human choice.",
            review_skip=acknowledgement(t),
            review_ack={
                "review_id": "review",
                "report_sha256": "b" * 64,
                "confirmed_reviewed": True,
            },
        )
