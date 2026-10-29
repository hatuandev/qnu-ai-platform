"""Reconstruct worker identity from server authority, never queue-supplied roles.

Ordinary actors continue through current DB membership checks. The fixed local
admin is issued only by the dev gate; re-resolve it only while that authority is
enabled and SSO is off, so an SSO subject collision cannot inherit local rights.
"""

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.dev_gate import (
    DEV_ADMIN_ACTOR_ID,
    dev_admin_actor,
    dev_gate_enabled,
)
from qnu.platform.config import get_settings


def background_actor(actor_id: str) -> AuthActor:
    settings = get_settings()
    if (
        actor_id == DEV_ADMIN_ACTOR_ID
        and dev_gate_enabled()
        and not settings.SSO_ENABLED
        and bool(settings.DEV_ACCESS_PASSWORD)
    ):
        return dev_admin_actor()
    return AuthActor(username=actor_id, actor_id=actor_id, roles=[], permissions=[])
