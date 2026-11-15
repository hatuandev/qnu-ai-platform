"""Deterministic checks for guardrail refusals; policy and wording stay model-owned."""

import re

from qnu.domains.assistants.guardrail_policy import GUARDRAIL_CATEGORIES

VERSION = "qnu.conversation.guardrail/v1"
CHECKS = ("figures", "contact")
# Directives the model follows but cannot be verified without domain data.
DIRECTIVE_ONLY = ("personal_data", "other_school")
FALLBACK = "Mình chưa thể hỗ trợ nội dung này. Bạn vui lòng hỏi câu khác trong phạm vi trợ lý nhé."
_DIGIT = re.compile(r"\d")
_CONTACT = re.compile(
    r"https?://|www\.|[\w.+-]+@[\w-]+\.[\w.]+|(?:\+?84|0)\d{8,10}", re.IGNORECASE
)


def categories(config: dict) -> list[str]:
    policy = (config.get("rag_policy") or {}).get("guardrail_policy") or {}
    if not policy.get("enabled"):
        return []
    return [item for item in policy.get("categories") or [] if item in GUARDRAIL_CATEGORIES]


def violations(answer: str) -> list[str]:
    found = []
    if _DIGIT.search(answer):
        found.append("figures")
    if _CONTACT.search(answer):
        found.append("contact")
    return found


def retry_note(found: list[str]) -> str:
    forbidden = []
    if "figures" in found:
        forbidden.append("không có bất kỳ chữ số nào")
    if "contact" in found:
        forbidden.append("không có email, đường dẫn hay số điện thoại")
    return (
        "Lời từ chối trước không đạt chính sách guardrail: "
        + "; ".join(forbidden)
        + ". Viết lại lời từ chối lịch sự, ngắn gọn, giữ nguyên guardrail_category "
        "và các quy tắc guardrail khác."
    )
