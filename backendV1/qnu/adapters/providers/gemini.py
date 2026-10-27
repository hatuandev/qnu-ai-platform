"""Placeholder adapter for Gemini chat.

Not implemented in Phase 0. It must raise instead of returning fabricated data;
implement it against the ModelOps runtime in the porting phase.
"""

from __future__ import annotations


class GeminiChatModel:
    name = "gemini"

    def __init__(self) -> None:
        raise NotImplementedError(
            "Gemini chat adapter chưa được triển khai trong backendV1 (Phase 0)."
        )
