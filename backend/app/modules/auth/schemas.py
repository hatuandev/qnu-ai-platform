"""Pydantic DTO schemas for Dev Access Gate authentication."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DevLoginRequest(BaseModel):
    access_key: str = Field(..., min_length=1, max_length=128, description="Mật khẩu truy cập môi trường Dev")


class AuthActor(BaseModel):
    username: str
    actor_id: str = "act_admin_qnu"
    display_name: str = "Cán bộ Quản trị QNU"
    tenant_id: str = "tenant_qnu"
    workspace_id: str = "workspace_qnu"
    role: str = "admin"
    session_version: str = "v1"
    authenticated: bool = True


class AuthStatusResponse(BaseModel):
    authenticated: bool
    actor: AuthActor | None = None
    message: str | None = None
