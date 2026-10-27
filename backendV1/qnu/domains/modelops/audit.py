"""Record safe configuration events in the caller's transaction."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.models import ModelOpsEvent
from qnu.domains.workspaces.access import actor_ref


def record_event(
    db: AsyncSession,
    actor: AuthActor,
    action: str,
    provider_id: str | None = None,
    fields: list[str] | None = None,
) -> None:
    db.add(
        ModelOpsEvent(
            id="moe_" + uuid.uuid4().hex[:16],
            actor_ref=actor_ref(actor),
            action=action,
            provider_id=provider_id,
            detail={"fields": sorted(fields or [])},
        )
    )
