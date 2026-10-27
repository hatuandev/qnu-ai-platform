"""Platform ModelOps permissions are independent of workspace membership roles."""

from qnu.domains.identity.actor import AuthActor
from qnu.platform.errors import Forbidden


def require_model_admin(actor: AuthActor) -> None:
    if not actor.authenticated or not actor.has_permission("ai.models.manage"):
        raise Forbidden("Chỉ quản trị ModelOps được cấp provider.", code="permission_denied")
