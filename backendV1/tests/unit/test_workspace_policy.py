"""Tests for pure workspace policy: identity, roles and migration ownership."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qnu.domains.identity.actor import AuthActor
from qnu.domains.workspaces.access import actor_ref, is_platform_admin
from qnu.domains.workspaces.schemas import MemberCreateRequest, WorkspaceCreateRequest
from qnu.platform.ownership import LEGACY_TABLES, include_object


def _platform() -> AuthActor:
    return AuthActor(
        username="root", actor_id="root", roles=["AI.Admin"], permissions=["ai.access.admin"]
    )


def _member() -> AuthActor:
    return AuthActor(username="cb", actor_id="CB_01", permissions=["ai.knowledge.view"])


def test_platform_admin_detected_by_workspace_permission() -> None:
    assert is_platform_admin(_platform()) is True
    assert is_platform_admin(_member()) is False


def test_actor_ref_preserves_case_sensitive_subject() -> None:
    assert actor_ref(AuthActor(username="x", actor_id="  SUB_AbC  ")) == "SUB_AbC"


def test_workspace_code_rejects_uppercase_and_spaces() -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreateRequest(code="Khoa CNTT", name="Khoa CNTT")
    assert WorkspaceCreateRequest(code="khoa-cntt", name="  Khoa CNTT ").name == "Khoa CNTT"


def test_member_role_is_limited() -> None:
    with pytest.raises(ValidationError):
        MemberCreateRequest(actor_ref="cb1", role="superuser")
    assert MemberCreateRequest(actor_ref="cb1").role == "member"


def test_alembic_filter_never_touches_legacy_tables() -> None:
    assert len(LEGACY_TABLES) == 49
    assert include_object(None, "workspaces", "table", False, None) is True
    assert include_object(None, "knowledge_collections", "table", False, None) is False
    assert include_object(None, "provider_api_keys", "table", False, None) is False
    assert include_object(None, "ix_any_index", "index", False, None) is True


def test_v1_models_do_not_collide_with_legacy_tables() -> None:
    from qnu.domains.workspaces.models import Base

    v1_tables = set(Base.metadata.tables)
    assert {"workspaces", "workspace_members", "workspace_events"} <= v1_tables
    assert not (v1_tables & LEGACY_TABLES)
