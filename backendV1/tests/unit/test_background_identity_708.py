"""Worker roles come from active server authority, not stored job claims."""

import pytest

from qnu.domains.identity.background import background_actor
from qnu.platform.config import get_settings


@pytest.mark.parametrize(
    ("enabled", "sso", "environment", "password", "ref", "allowed"),
    [
        (True, False, "development", "synthetic", "act_dev_admin", True),
        (False, False, "development", "synthetic", "act_dev_admin", False),
        (True, True, "development", "synthetic", "act_dev_admin", False),
        (True, False, "production", "synthetic", "act_dev_admin", False),
        (True, False, "development", "", "act_dev_admin", False),
        (True, False, "development", "synthetic", "act_dev_ctsv_admin", False),
        (True, False, "development", "synthetic", "dev.admin", False),
    ],
)
def test_local_admin_requires_current_authority(monkeypatch, enabled, sso, environment, password, ref, allowed):
    settings = get_settings()
    monkeypatch.setattr(settings, "DEV_AUTH_ENABLED", enabled)
    monkeypatch.setattr(settings, "SSO_ENABLED", sso)
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(settings, "DEV_ACCESS_PASSWORD", password)
    actor = background_actor(ref)
    assert actor.actor_id == ref
    assert actor.has_permission("ai.workspaces.manage") is allowed
    if not allowed:
        assert actor.roles == actor.permissions == []
