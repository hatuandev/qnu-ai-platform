"""RFC 7807 problem detail contract."""

from __future__ import annotations

from pydantic import BaseModel, Field

ERROR_BASE_URL = "https://errors.qnu.edu.vn/"


def problem_type(code: str) -> str:
    return f"{ERROR_BASE_URL}{code}"


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    code: str
    correlation_id: str | None = None
    errors: dict[str, list[str]] | None = Field(default=None)
