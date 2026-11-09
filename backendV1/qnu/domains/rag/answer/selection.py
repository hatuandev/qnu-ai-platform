"""Question-aware evidence selection; retrieval candidates are not all mandatory evidence."""

import json
import re
import unicodedata

from qnu.domains.knowledge.index.schemas import SearchHit

VERSION = "qnu.rag.selection/v2"

_SINGLE_VALUE = re.compile(
    r"\b(?:bao nhiêu|mấy|số lượng|tỷ lệ|phần trăm|chỉ tiêu|điểm chuẩn|học phí|"
    r"how many|how much|what (?:is|was) the (?:number|rate|fee|score|quota))\b",
    re.IGNORECASE,
)
_CONDITION = re.compile(
    r"\b(?:điều kiện|trường hợp|nếu|khi|ngoại lệ|miễn|giảm|hồ sơ|thủ tục|"
    r"đối tượng|áp dụng|conditions?|exceptions?|eligib\w*)\b",
    re.IGNORECASE,
)
_ENUMERATION = re.compile(
    r"\b(?:liệt kê|danh sách|những|các|gồm|bao gồm|toàn bộ|tất cả|"
    r"list|all|requirements|steps)\b",
    re.IGNORECASE,
)
_COMPARISON = re.compile(
    r"\b(?:so sánh|khác|chênh|lệch|cao nhất|thấp nhất|nhiều nhất|ít nhất|hơn|"
    r"compare|difference|highest|lowest)\b",
    re.IGNORECASE,
)


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split()).casefold()


def question_needs(question: str, resolved_question: str | None = None) -> dict:
    """Deterministic cues only; never a per-question model plan or corpus vocabulary."""
    resolved = resolved_question or ""
    follow_up = bool(resolved.strip()) and _normalized(resolved) != _normalized(question)
    needs = {
        "single_value": bool(_SINGLE_VALUE.search(question)),
        "condition": bool(_CONDITION.search(question)),
        "enumeration": bool(_ENUMERATION.search(question)),
        "comparison": bool(_COMPARISON.search(question)),
        "follow_up": follow_up,
    }
    needs["kind"] = next(
        (
            kind
            for kind in ("enumeration", "condition", "comparison", "single_value")
            if needs[kind]
        ),
        "follow_up" if follow_up else "general",
    )
    return needs


def _required(context: dict) -> set[str]:
    required = set(context.get("support_ids") or [])
    required.update(item["chunk_id"] for item in context.get("added") or [])
    for link in context.get("table_links") or []:
        required.add(link["chunk_id"])
        required.update(link.get("support_ids") or [])
    for group in context.get("structure", {}).get("groups") or []:
        required.update(group.get("required_ids") or [])
    return required


def _dedupe_key(hit: SearchHit) -> tuple | None:
    if hit.kind == "table":
        return None
    return (
        hit.document_id,
        hit.version_id,
        hit.publication_decision_id,
        hit.kind,
        _normalized(hit.text),
        json.dumps(hit.citations, ensure_ascii=False, sort_keys=True),
        json.dumps(hit.structure, ensure_ascii=False, sort_keys=True),
    )


def select_hits(
    hits: list[SearchHit],
    context: dict,
    question: str,
    *,
    resolved_question: str | None = None,
) -> tuple[list[SearchHit], dict]:
    """Keep source coverage; compact serialization before imposing rank cutoffs.

    Question cues are trace metadata, not proof that lower-ranked rules are
    irrelevant. Only identical source-bound narrative duplicates may be omitted.
    """
    needs = question_needs(question, resolved_question)
    primary = list(context.get("primary_ids") or [])
    primary_rank = {chunk_id: rank for rank, chunk_id in enumerate(primary)}
    required = _required(context)
    seen: dict[tuple, str] = {}
    selected, dropped = [], []
    for hit in hits:
        is_primary = hit.chunk_id in primary_rank or not primary
        if not is_primary or hit.chunk_id in required or hit.kind == "table":
            selected.append(hit)
            continue
        key = _dedupe_key(hit)
        if key is not None and key in seen:
            dropped.append({"chunk_id": hit.chunk_id, "kind": hit.kind, "reason": "duplicate"})
            continue
        if key is not None:
            seen[key] = hit.chunk_id
        selected.append(hit)
    return selected, {
        "version": VERSION,
        "needs": needs,
        "policy": "exact_source_duplicates_only",
        "retrieved_count": len(hits),
        "selected_count": len(selected),
        "selected_ids": [hit.chunk_id for hit in selected],
        "selected": {
            "tables": sum(hit.kind == "table" for hit in selected),
            "narrative": sum(hit.kind != "table" for hit in selected),
            "required": len(required & {hit.chunk_id for hit in hits}),
        },
        "dropped_count": len(dropped),
        "dropped": dropped[:20],
    }
