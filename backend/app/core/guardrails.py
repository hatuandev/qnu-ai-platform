"""Input & Output Guardrails — Prompt Injection, Jailbreak Defense & Content Safety."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Common Prompt Injection & Jailbreak attack patterns (both English and Vietnamese)
PROMPT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    # Override instructions
    re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|commands)",
        re.IGNORECASE,
    ),
    re.compile(
        r"bỏ\s+qua\s+(toàn\s+bộ\s+)?(các\s+)?(hướng\s+dẫn|chỉ\s+thị|quy\s+tắc|câu\s+lệnh)\s+(trước|trên)",
        re.IGNORECASE,
    ),
    re.compile(r"quên\s+(hết|toàn\s+bộ)\s+(các\s+)?(hướng\s+dẫn|chỉ\s+thị)", re.IGNORECASE),
    # System prompt extraction
    re.compile(
        r"(reveal|show|print|display|output|repeat|tell\s+me)\s+(your\s+)?(system\s+prompt|initial\s+prompt|instructions)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(tiết\s+lộ|in\s+ra|hiển\s+thị|cho\s+tôi\s+biết)\s+(prompt\s+hệ\s+thống|chỉ\s+thị\s+ban\s+đầu|lệnh\s+hệ\s+thống)",
        re.IGNORECASE,
    ),
    # Role-play jailbreaks (DAN, Evil bot, Developer Mode)
    re.compile(
        r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|jailbroken|unrestricted)", re.IGNORECASE
    ),
    re.compile(
        r"bây\s+giờ\s+bạn\s+là\s+(chế\s+độ\s+nhà\s+phát\s+triển|không\s+bị\s+giới\s+hạn)",
        re.IGNORECASE,
    ),
    re.compile(r"act\s+as\s+an\s+unfiltered|unrestricted\s+ai", re.IGNORECASE),
    # Secret leaking attempts
    re.compile(
        r"(reveal|show|leak|output)\s+(api\s+key|secret\s+key|password|database\s+url)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(tiết\s+lộ|cho\s+biết)\s+(khóa\s+api|api\s+key|mật\s+khẩu|chuỗi\s+kết\s+nối)",
        re.IGNORECASE,
    ),
]


@dataclass
class GuardrailResult:
    """Result of guardrail safety evaluation."""

    is_safe: bool
    risk_type: str | None = None
    reason: str | None = None
    sanitized_text: str = ""


class InputGuardrail:
    """Scans incoming user messages for prompt injection and adversarial attacks."""

    def __init__(self, patterns: list[re.Pattern[str]] | None = None):
        self.patterns = patterns or PROMPT_INJECTION_PATTERNS

    def check(self, text: str) -> GuardrailResult:
        if not text or not text.strip():
            return GuardrailResult(is_safe=True, sanitized_text=text)

        clean_text = text.strip()
        for pattern in self.patterns:
            match = pattern.search(clean_text)
            if match:
                matched_str = match.group(0)
                logger.warning(
                    "Prompt Injection detected: pattern='%s', text='%s'",
                    matched_str,
                    clean_text[:100],
                )
                return GuardrailResult(
                    is_safe=False,
                    risk_type="prompt_injection",
                    reason=f"Yêu cầu chứa mẫu lệnh không được phép: '{matched_str}'.",
                    sanitized_text=clean_text,
                )

        return GuardrailResult(
            is_safe=True,
            risk_type=None,
            reason=None,
            sanitized_text=clean_text,
        )


class OutputGuardrail:
    """Verifies outgoing LLM responses to prevent system leaks or toxic contents."""

    LEAK_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"sk-(?:proj-)?[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),  # OpenAI API key pattern
        re.compile(r"postgresql(\+asyncpg)?://\w+:[^@]+@", re.IGNORECASE),  # Database URL leak
    ]

    def check(self, response_text: str) -> GuardrailResult:
        if not response_text:
            return GuardrailResult(is_safe=True, sanitized_text=response_text)

        sanitized = response_text
        for pattern in self.LEAK_PATTERNS:
            if pattern.search(sanitized):
                logger.critical("Output leak detected in LLM response! Masking secret...")
                sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

        return GuardrailResult(
            is_safe=True,
            sanitized_text=sanitized,
        )


input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()
