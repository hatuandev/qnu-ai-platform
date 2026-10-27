"""SSE event envelope shared by chat and job streams."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

EventName = Literal["status", "token", "citation", "artifact", "approval_required", "done", "error"]


@dataclass(slots=True)
class StreamEvent:
    name: EventName
    data: dict[str, Any] = field(default_factory=dict)

    def encode(self) -> str:
        body = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.name}\ndata: {body}\n\n"
