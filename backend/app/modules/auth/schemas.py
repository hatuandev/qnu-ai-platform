"""Pydantic DTO schemas for Authentication & QNU SSO Integration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DevLoginRequest(BaseModel):
    access_key: str = Field(..., min_length=1, max_length=128, description="Mật khẩu truy cập môi trường Dev")


class AuthActor(BaseModel):
    username: str
    actor_id: str = "act_admin_qnu"
    display_name: str = "Cán bộ Quản trị QNU"
    email: str | None = None
    user_type: str = "staff"
    student_id: str | None = None
    tenant_id: str = "tenant_qnu"
    workspace_id: str = "workspace_qnu"
    role: str = "staff"
    roles: list[str] = Field(default_factory=lambda: ["staff"])
    permissions: list[str] = Field(default_factory=list)
    session_version: str = "v1"
    authenticated: bool = True

    def has_permission(self, permission: str) -> bool:
        """Check whether actor has a specific permission or full ai.* access via AI.Admin / ai.access.admin."""
        if not permission:
            return True
        p = permission.strip().lower()
        perms = {item.strip().lower() for item in self.permissions}
        actor_roles = {r.strip().lower() for r in self.roles}

        # 1. Exact match on declared permission
        if p in perms:
            return True

        # 2. ai.access.admin permission or exact AI.Admin role grants all ai.* permissions
        return bool(("ai.admin" in actor_roles or "ai.access.admin" in perms) and p.startswith("ai."))


class AuthStatusResponse(BaseModel):
    authenticated: bool
    actor: AuthActor | None = None
    message: str | None = None
