"""Assistants Module — 05 Standard AI Assistants for QNU Platform."""

from __future__ import annotations

from app.modules.assistants.router import (
    chat_router as assistant_chat_router,
)
from app.modules.assistants.router import (
    router as assistants_router,
)
from app.modules.assistants.service import assistant_service

__all__ = ["assistant_chat_router", "assistant_service", "assistants_router"]
