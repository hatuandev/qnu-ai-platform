"""Permission dependency factory."""

from __future__ import annotations

from fastapi import Depends

from qnu.domains.identity.actor import AuthActor
from qnu.platform.errors import Forbidden


def require_permission(permission: str):
    """Return a dependency that fails closed with a stable error code."""

    from qnu.api.dependencies import get_actor  # local import avoids an import cycle

    async def _dependency(actor: AuthActor = Depends(get_actor)) -> AuthActor:
        if not actor.has_permission(permission):
            raise Forbidden(
                f"Tài khoản '{actor.username}' không có quyền '{permission}'.",
                code="permission_denied",
            )
        return actor

    return _dependency
