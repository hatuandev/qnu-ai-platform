"""Condition Route Node Handler — Evaluates intents and routes DAG execution."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from typing import Any

from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

# Universal morphological greeting root stems
_GREETING_ROOT_STEMS: frozenset[str] = frozenset(
    {"chào", "hello", "hi", "hey", "cảm ơn", "cm ơn", "thanks", "thank you", "tạm biệt", "bye"}
)

# Polite greeting prefixes (morphological modifiers)
_GREETING_PREFIX_PATTERN = re.compile(r"\b(?:xin|kính|chúc)\s+", re.IGNORECASE)

# Generalized administrative & organizational morphology pattern
_ORGANIZATIONAL_ENTITY_PATTERN = re.compile(
    r"\b(?:trợ\s+lý|phòng|ban|trung\s+tâm|khoa|viện|trường|thư\s+viện|đoàn|hội|hội\s+đồng|bộ\s+môn)"
    r"(?:\s+[^,!?.\n]+?)?(?=[,!?.\n]|\s+(?:cho|hỏi|tư\s+vấn|xét|điểm|lấy|học|cần|muốn|được|ạ|ơi|nhé|nha)|\s*$)",
    re.IGNORECASE,
)

# Polite pronouns and modal particles
_POLITE_PRONOUNS_AND_PARTICLES = re.compile(
    r"\b(?:thầy\s+cô|quý\s+thầy\s+cô|quý\s+vị|thầy|cô|anh|chị|em|bạn|mình|qnu(?:\.ai)?|bot|ai|ad|admin|ạ|nhé|nha|ơi|với|nhỉ|cho\s+(?:tôi|em|mình|chúng\s+tôi))\b",
    re.IGNORECASE,
)

# Syntactic interrogative and question-seeking constructs
_SYNTACTIC_INTERROGATIVE_PATTERN = re.compile(
    r"\b(?:bao\s+(?:nhiêu|lâu|giờ)|khi\s+nào|thế\s+nào|như\s+thế\s+nào|ra\s+sao|làm\s+sao|tại\s+sao|vì\s+sao|do\s+đâu|cho\s+hỏi|xin\s+hỏi|hỏi|thắc\s+mắc|hướng\s+dẫn|tư\s+vấn|liệu|phải\s+không|đúng\s+không|chưa|có\s+(?:được|thể)|muốn\s+biết|tìm\s+hiểu|gì|nào|mấy|sao|đâu)\b",
    re.IGNORECASE,
)


def _is_pure_greeting(message: str, tokens: list[str]) -> bool:
    """Check if the message is purely a greeting rather than a substantive inquiry/question.

    Uses syntactic & morphological invariants:
    1. If message contains a question mark '?', it is NEVER a pure greeting.
    2. If any universal interrogative/question particle is present, it is an inquiry.
    3. Strips organizational addressees and administrative titles.
    4. Strips polite prefixes, pronouns and modal particles.
    5. Strips greeting root stems and configured rule tokens.
    6. If meaningful substantive content (> 2 words or substantive length) remains, it is NOT a pure greeting.
    7. Pure greeting holds only when the cleaned remainder is negligible (<= 2 characters).
    """
    clean_msg = unicodedata.normalize("NFC", message.strip().lower())
    if not clean_msg:
        return False

    # 1. Any question mark indicates a real inquiry, never a pure greeting
    if "?" in clean_msg:
        return False

    # 2. Universal syntactic question / inquiry indicators
    if _SYNTACTIC_INTERROGATIVE_PATTERN.search(clean_msg):
        return False

    # 3. Strip organizational addressees and administrative titles
    remainder = _ORGANIZATIONAL_ENTITY_PATTERN.sub(" ", clean_msg)

    # 4. Strip polite prefixes, pronouns and particles
    remainder = _GREETING_PREFIX_PATTERN.sub(" ", remainder)
    remainder = _POLITE_PRONOUNS_AND_PARTICLES.sub(" ", remainder)

    # 5. Strip greeting roots and rule tokens
    all_greetings = list(_GREETING_ROOT_STEMS)
    for t in tokens:
        clean_t = re.sub(r"[^\w\s]", "", t).strip().lower()
        if clean_t and clean_t not in all_greetings:
            all_greetings.append(clean_t)

    for g in sorted(all_greetings, key=len, reverse=True):
        remainder = re.sub(
            r"(?:^|\W)" + re.escape(g) + r"(?:\W|$)", " ", remainder, flags=re.IGNORECASE
        )

    clean_remainder = re.sub(r"[!.,~:;/\-_\s]+", "", remainder)

    # 6. Check remaining substantive word count
    remaining_words = [
        w for w in re.findall(r"\b\w{2,}\b", remainder) if w not in all_greetings
    ]
    if len(remaining_words) >= 2 or len(clean_remainder) >= 8:
        return False

    return len(clean_remainder) <= 2


async def _classify_intent_with_llm(
    context: WorkflowContext,
    message: str,
    rules: list[dict[str, Any]],
    default_node: str | None,
) -> tuple[str | None, str | None]:
    """Call fast LLM to disambiguate intent when deterministic rules yield low confidence.

    Returns:
        (next_target_node, matched_rule_id)
    """
    if not context.db or not rules or not message.strip():
        return default_node, None

    candidate_descriptions: list[str] = []
    rule_map: dict[str, dict[str, Any]] = {}
    for r in rules:
        r_id = r.get("id")
        if not r_id:
            continue
        rule_map[r_id] = r
        desc = r.get("description") or r.get("match", {}).get("intent") or r_id
        candidate_descriptions.append(f"- ID: '{r_id}' -> Ý định: {desc}")

    if not candidate_descriptions:
        return default_node, None

    prompt = (
        "Bạn là bộ phân loại ý định (Intent Classifier) cho hệ thống trợ lý đại học.\n"
        "Hãy phân loại câu người dùng vào MỘT trong các Rule ID sau:\n"
        f"{chr(10).join(candidate_descriptions)}\n"
        "- ID: 'default' -> Nếu không khớp rõ ràng với bất kỳ rule nào ở trên.\n\n"
        f'Câu của người dùng: "{message.strip()}"\n\n'
        "CHỈ trả về JSON duy nhất (không giải thích thêm):\n"
        '{"rule_id": "<ID_ĐÃ_CHỌN>", "confidence": 0.95}'
    )

    profile = context.assistant_profile
    primary_model = (
        profile.model_policy.primary_model
        if (profile and hasattr(profile, "model_policy") and profile.model_policy)
        else None
    )
    fallback_model = (
        profile.model_policy.fallback_model
        if (profile and hasattr(profile, "model_policy") and profile.model_policy)
        else None
    )
    preferred_provider_id = (
        getattr(profile.model_policy, "preferred_provider_id", None)
        if (profile and hasattr(profile, "model_policy") and profile.model_policy)
        else None
    )

    req = LLMGenerateRequest(
        messages=[ChatMessage(role="user", content=prompt)],
        temperature=0.0,
        max_tokens=50,
        thinking_budget=0,
        preferred_provider_id=preferred_provider_id,
        preferred_model_name=primary_model,
        fallback_model_name=fallback_model,
    )

    try:
        res = await asyncio.wait_for(
            modelops_service.generate(context.db, req),
            timeout=1.5,
        )
        content = res.content.strip()
        m = re.search(r"\{.*?\}", content, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            rule_id = data.get("rule_id", "").strip()
            confidence = float(data.get("confidence", 0.0))
            if rule_id in rule_map and confidence >= 0.65:
                matched_rule = rule_map[rule_id]
                logger.info(
                    "LLM classified intent for '%s' -> rule '%s' (conf=%.2f)",
                    message[:40],
                    rule_id,
                    confidence,
                )
                return matched_rule.get("to", default_node), rule_id
    except Exception as exc:
        logger.debug("Micro-LLM intent classification skipped or timed out: %s", exc)

    return default_node, None


class ConditionRouteNodeHandler(BaseNodeHandler):
    """Branches DAG execution based on intent matching rules."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        message = context.node_data.get("user_message", "").lower()
        config = node_spec.config or {}
        rules = config.get("rules", [])
        default_node = config.get("default_node")

        next_target = default_node
        matched_rule_id = None

        # 1. Deterministic Fast-Path Pass (0ms)
        for rule in rules:
            match_spec = rule.get("match", {})
            pattern = match_spec.get("intent")
            if pattern:
                is_greeting_rule = (
                    "chào" in pattern.lower()
                    or "hello" in pattern.lower()
                    or "greet" in rule.get("id", "").lower()
                )
                if is_greeting_rule:
                    clean_pat = re.sub(r"\\[bBsSwWdD]", " ", pattern)
                    clean_pat = re.sub(r"[()?:^$+*]", " ", clean_pat)
                    greeting_tokens = [
                        re.sub(r"\s+", " ", t).strip()
                        for t in clean_pat.split("|")
                        if t.strip()
                    ]
                    if _is_pure_greeting(message, greeting_tokens):
                        next_target = rule.get("to")
                        matched_rule_id = rule.get("id")
                        break
                else:
                    # Direct regex evaluation first
                    is_match = False
                    try:
                        if re.search(pattern, message, re.IGNORECASE):
                            is_match = True
                    except re.error:
                        pass

                    # Fallback keyword token matching with word boundaries
                    if not is_match:
                        tokens = [t.strip() for t in pattern.split("|") if t.strip()]
                        safe_regex = (
                            r"(?:^|\W)(?:"
                            + "|".join(re.escape(t) for t in tokens)
                            + r")(?:\W|$)"
                        )
                        if re.search(safe_regex, message, re.IGNORECASE):
                            is_match = True

                    if is_match:
                        next_target = rule.get("to")
                        matched_rule_id = rule.get("id")
                        break

        # 2. Micro-LLM Disambiguation (if deterministic didn't match and substantive message exists)
        if matched_rule_id is None and len(message.strip()) > 3 and rules:
            llm_target, llm_rule_id = await _classify_intent_with_llm(
                context=context,
                message=message,
                rules=rules,
                default_node=default_node,
            )
            if llm_rule_id:
                next_target = llm_target
                matched_rule_id = llm_rule_id

        context.node_data["routed_to"] = next_target
        context.node_data["matched_rule_id"] = matched_rule_id

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "next_node": next_target,
                "matched_rule_id": matched_rule_id,
                "message": context.node_data.get("user_message", ""),
                "response": context.node_data.get("user_message", ""),
            },
            next_node_override=next_target,
        )
