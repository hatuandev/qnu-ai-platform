"""Identity DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from qnu.domains.identity.actor import AuthActor


class DevLoginRequest(BaseModel):
    access_key: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800


class ActorResponse(BaseModel):
    actor: AuthActor


class LogoutResponse(BaseModel):
    status: str = "ok"
