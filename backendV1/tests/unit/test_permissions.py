"""Permission semantics for AuthActor."""

from __future__ import annotations

from qnu.domains.identity.actor import AuthActor


def test_exact_permission_is_granted() -> None:
    actor = AuthActor(username="a", permissions=["ai.knowledge.view"])
    assert actor.has_permission("ai.knowledge.view") is True
    assert actor.has_permission("ai.knowledge.upload") is False


def test_access_admin_grants_any_ai_permission_only() -> None:
    actor = AuthActor(username="a", roles=["AI.Admin"], permissions=["ai.access.admin"])
    assert actor.has_permission("ai.knowledge.delete") is True
    assert actor.has_permission("users.read") is False
