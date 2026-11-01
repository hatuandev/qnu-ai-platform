"""Declared reasoning control for one provider/model; never inferred from a name.

A provider only receives a reasoning parameter when an administrator declared the
exact parameter, the value for each level and marked the capability verified by a
probe. Anything else keeps the server default and says so in the trace. This module
never guesses ``enable_thinking``/``reasoning_effort``/``chat_template_kwargs`` for
an endpoint, and it never changes a running request silently.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qnu.platform.errors import AppException

EXTRA_CONFIG_KEY = "reasoning_policy_v1"
ReasoningMode = Literal["server_default", "effort", "toggle", "chat_template_kwarg"]
ReasoningLevel = Literal["off", "low"]
# Tasks whose prompt is owned by QNU and where reasoning can be tuned safely.
REASONING_TASKS = ("compiler", "compiler_review", "answer", "ocr_review")
REASONING_LEVELS = ("off", "low")
PARAMETER_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"


def _invalid(detail: str) -> AppException:
    return AppException(
        detail,
        code="modelops_reasoning_policy_invalid",
        status_code=422,
        title="Chính sách reasoning không hợp lệ",
    )


class ReasoningPolicy(BaseModel):
    """Administrator-declared contract; ``server_default`` sends no parameter."""

    model_config = ConfigDict(extra="forbid", strict=True)
    mode: ReasoningMode = "server_default"
    parameter: str | None = Field(None, min_length=1, max_length=64)
    low_value: bool | int | float | str | None = None
    off_value: bool | int | float | str | None = None
    tasks: dict[ReasoningLevel, list[str]] | None = None
    verified: bool = False
    note: str | None = Field(None, max_length=300)

    @field_validator("parameter")
    @classmethod
    def simple_parameter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        import re

        if not re.fullmatch(PARAMETER_PATTERN, value):
            raise ValueError("Tên tham số phải là khóa JSON đơn giản, không dấu chấm.")
        return value

    @model_validator(mode="after")
    def coherent(self):
        if self.mode == "server_default":
            if self.parameter is not None or self.low_value is not None or self.off_value is not None:
                raise ValueError("Chế độ server_default không gửi tham số nào.")
            return self
        if self.parameter is None:
            raise ValueError("Cần khai báo đúng tên tham số do provider hỗ trợ.")
        levels = self.tasks or {}
        # ``tasks`` maps a level to the tasks using it; a task may not appear twice.
        seen: dict[str, str] = {}
        for level, tasks in levels.items():
            if level not in REASONING_LEVELS:
                raise ValueError("Mức reasoning chỉ nhận 'off' hoặc 'low'.")
            if not tasks:
                raise ValueError("Mỗi mức reasoning phải nêu ít nhất một tác vụ.")
            if len(tasks) != len(set(tasks)) or set(tasks) - set(REASONING_TASKS):
                raise ValueError("Danh sách tác vụ reasoning không hợp lệ hoặc bị trùng.")
            for task in tasks:
                if task in seen:
                    raise ValueError("Một tác vụ chỉ được khai báo ở một mức reasoning.")
                seen[task] = level
            if level == "off" and self.off_value is None:
                raise ValueError("Thiếu giá trị 'off' cho tham số đã khai báo.")
            if level == "low" and self.low_value is None:
                raise ValueError("Thiếu giá trị 'low' cho tham số đã khai báo.")
        return self

    def level_for(self, task: str) -> ReasoningLevel | None:
        for level, tasks in (self.tasks or {}).items():
            if task in tasks:
                return level
        return None

    def value_for(self, level: ReasoningLevel) -> Any:
        return self.off_value if level == "off" else self.low_value

    def public_dict(self) -> dict[str, Any]:
        """Safe description for traces: declared contract, never a credential."""
        return {
            "mode": self.mode,
            "parameter": self.parameter,
            "tasks": self.tasks or {},
            "verified": self.verified,
            "status": self.status,
        }

    @property
    def status(self) -> str:
        if self.mode == "server_default":
            return "server_default"
        return "active" if self.verified else "unverified"


@dataclass(frozen=True, slots=True)
class ReasoningDirective:
    """One concrete parameter to add to a request body for a single task."""

    mode: str
    parameter: str
    value: Any
    level: str
    policy_sha256: str

    def apply(self, payload: dict[str, Any]) -> None:
        if self.mode == "chat_template_kwarg":
            kwargs = payload.setdefault("chat_template_kwargs", {})
            kwargs[self.parameter] = self.value
        else:
            payload[self.parameter] = self.value

    def public_dict(self) -> dict[str, Any]:
        """Exact request contract for trace/replay; a parameter value is not a secret."""
        return {
            "mode": self.mode,
            "parameter": self.parameter,
            "value": self.value,
            "level": self.level,
            "policy_sha256": self.policy_sha256,
        }

    @classmethod
    def from_public_dict(cls, value: dict[str, Any] | None) -> ReasoningDirective | None:
        """Rebuild a stored directive; a corrupted record fails instead of guessing."""
        if not value:
            return None
        try:
            directive = cls(
                mode=str(value["mode"]),
                parameter=str(value["parameter"]),
                value=value["value"],
                level=str(value["level"]),
                policy_sha256=str(value["policy_sha256"]),
            )
        except (KeyError, TypeError) as exc:
            raise _invalid("Bản ghi reasoning đã lưu không đọc được.") from exc
        if directive.mode not in {"effort", "toggle", "chat_template_kwarg"}:
            raise _invalid("Bản ghi reasoning đã lưu sai chế độ.")
        if directive.level not in {"off", "low"}:
            raise _invalid("Bản ghi reasoning đã lưu sai mức.")
        if value.get("value") is None or not isinstance(directive.parameter, str):
            raise _invalid("Bản ghi reasoning đã lưu thiếu tham số.")
        return directive


def policy_digest(policy: ReasoningPolicy) -> str:
    material = {
        "mode": policy.mode,
        "parameter": policy.parameter,
        "low_value": policy.low_value,
        "off_value": policy.off_value,
        "tasks": policy.tasks or {},
        "verified": policy.verified,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def parse_policy(value: Any) -> ReasoningPolicy | None:
    """Read the stored contract; an invalid record is never applied."""
    if value is None:
        return None
    if not isinstance(value, dict):
        return None
    try:
        return ReasoningPolicy.model_validate(value)
    except Exception:  # Invalid stored JSON must not break every request
        return None


def resolve_directive(
    policy: ReasoningPolicy | None, task: str
) -> ReasoningDirective | None:
    """Return the parameter to send, or ``None`` to keep the server default."""
    if policy is None or policy.mode == "server_default" or not policy.verified:
        return None
    level = policy.level_for(task)
    if level is None:
        return None
    value = policy.value_for(level)
    if value is None or policy.parameter is None:
        return None
    return ReasoningDirective(
        mode=policy.mode,
        parameter=policy.parameter,
        value=value,
        level=level,
        policy_sha256=policy_digest(policy),
    )


def trace_for(policy: ReasoningPolicy | None, task: str) -> dict[str, Any]:
    """Always explain the effective decision, including 'server default'."""
    directive = resolve_directive(policy, task)
    if directive is not None:
        return {**directive.public_dict(), "applied": True}
    return {
        "applied": False,
        "status": policy.status if policy is not None else "not_configured",
        "mode": policy.mode if policy is not None else "server_default",
        "parameter": policy.parameter if policy is not None else None,
        "reason": (
            "provider_keeps_server_default"
            if policy is None or policy.mode == "server_default"
            else "capability_not_verified"
            if not policy.verified
            else "task_not_configured"
        ),
    }
