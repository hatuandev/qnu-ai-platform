"""Authenticated actor contract and permission checks."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthActor(BaseModel):
    username: str
    actor_id: str = "unknown"
    display_name: str = "Người dùng"
    email: str | None = None
    user_type: str = "staff"
    role: str = "staff"
    roles: list[str] = Field(default_factory=lambda: ["staff"])
    permissions: list[str] = Field(default_factory=list)
    authenticated: bool = True

    def has_permission(self, permission: str) -> bool:
        """Exact permission, or any ``ai.*`` permission for AI.Admin / ai.access.admin."""
        if not self.authenticated:
            return False
        if not permission:
            return True
        wanted = permission.strip().lower()
        granted = {item.strip().lower() for item in self.permissions}
        if wanted in granted:
            return True
        roles = {item.strip().lower() for item in self.roles}
        is_admin = "ai.admin" in roles or "ai.access.admin" in granted
        return bool(is_admin and wanted.startswith("ai."))
