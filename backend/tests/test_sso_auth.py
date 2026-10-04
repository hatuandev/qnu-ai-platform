"""Unit tests for QNU Single Sign-On (OIDC) integration & fine-grained RBAC."""

from __future__ import annotations

import pytest

from app.modules.auth.schemas import AuthActor
from app.modules.auth.sso_validator import parse_sso_claims, validate_sso_token


def test_parse_sso_claims_staff():
    claims = {
        "sub": "user_staff_001",
        "email": "nguyenvana@qnu.edu.vn",
        "name": "Nguyễn Văn A",
        "preferred_username": "nguyenvana",
        "role": "staff",
        "permission": ["ai.access.read", "ai.chat.access", "ai.assistants.view"],
    }
    actor = parse_sso_claims(claims)
    assert actor.actor_id == "user_staff_001"
    assert actor.username == "nguyenvana"
    assert actor.email == "nguyenvana@qnu.edu.vn"
    assert actor.display_name == "Nguyễn Văn A"
    assert actor.user_type == "staff"
    assert actor.has_permission("ai.access.read") is True
    assert actor.has_permission("ai.chat.access") is True
    assert actor.has_permission("ai.assistants.create") is False


def test_parse_sso_claims_admin_wildcard():
    claims = {
        "sub": "admin_001",
        "email": "admin@qnu.edu.vn",
        "name": "Quản Trị Viên",
        "roles": ["Administrator"],
        "permissions": ["*"],
    }
    actor = parse_sso_claims(claims)
    assert actor.role == "admin"
    assert actor.has_permission("ai.access.admin") is True
    assert actor.has_permission("ai.models.manage") is True
    assert actor.has_permission("any.unknown.permission") is True


def test_parse_sso_claims_student():
    claims = {
        "sub": "std_4551050001",
        "email": "4551050001@qnu.edu.vn",
        "name": "Trần Thị B",
        "preferred_username": "4551050001",
        "user_type": "student",
        "student_id": "4551050001",
    }
    actor = parse_sso_claims(claims)
    assert actor.student_id == "4551050001"
    assert actor.user_type == "student"
    assert actor.has_permission("ai.chat.access") is True
    assert actor.has_permission("ai.knowledge.upload") is False


@pytest.mark.asyncio
async def test_validate_sso_token_empty():
    actor = await validate_sso_token("")
    assert actor is None


@pytest.mark.asyncio
async def test_validate_sso_token_invalid_format():
    actor = await validate_sso_token("not-a-valid-jwt-token")
    assert actor is None


@pytest.mark.asyncio
async def test_require_permission_allows_authorized_actor():
    from app.modules.auth.dependencies import require_permission

    actor = AuthActor(
        actor_id="user_editor",
        username="editor",
        permissions=["ai.assistants.create"],
    )
    dep = require_permission("ai.assistants.create")
    resolved = await dep(actor=actor)
    assert resolved.username == "editor"


@pytest.mark.asyncio
async def test_require_permission_rejects_unauthorized_actor():
    from app.core.exceptions import AppException
    from app.modules.auth.dependencies import require_permission

    actor = AuthActor(
        actor_id="user_viewer",
        username="viewer",
        permissions=["ai.assistants.view"],
    )
    dep = require_permission("ai.assistants.delete")
    with pytest.raises(AppException) as exc_info:
        await dep(actor=actor)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"
    assert "không có quyền 'ai.assistants.delete'" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_require_permission_allows_manager_or_admin():
    from app.modules.auth.dependencies import require_permission

    manager = AuthActor(
        actor_id="user_manager",
        username="manager",
        permissions=["ai.access.manage"],
    )
    dep = require_permission("ai.assistants.publish")
    resolved = await dep(actor=manager)
    assert resolved.username == "manager"

    admin = AuthActor(
        actor_id="user_admin",
        username="admin",
        roles=["admin"],
        permissions=["*"],
    )
    resolved_admin = await dep(actor=admin)
    assert resolved_admin.username == "admin"

