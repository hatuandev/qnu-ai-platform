"""Identity endpoints (dev gate in Phase 0, SSO next)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.dev_gate import issue_dev_token
from qnu.domains.identity.schemas import (
    ActorResponse,
    DevLoginRequest,
    LogoutResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập dev gate")
async def login(body: DevLoginRequest) -> TokenResponse:
    token, _actor = await asyncio.to_thread(issue_dev_token, body.access_key)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=ActorResponse, summary="Actor hiện tại")
async def me(actor: AuthActor = Depends(get_actor)) -> ActorResponse:
    return ActorResponse(actor=actor)


@router.post("/logout", response_model=LogoutResponse, summary="Đăng xuất")
async def logout() -> LogoutResponse:
    return LogoutResponse()
