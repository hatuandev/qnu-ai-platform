"""Content-free retrieval telemetry; facts and exhaustive lists are separate paths."""

from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.intent_debug import intent_debug_enabled
from app.modules.rag.schemas import AskRequest, AskResponse


def attach_diagnostics(req: AskRequest, response: AskResponse) -> AskResponse:
    trace = dict(req._retrieval_diagnostics)
    if not intent_debug_enabled():
        trace.pop('fact_resolution', None)
    trace.setdefault("branch", "structured_or_dialogue")
    trace.setdefault("retrieval_executed", False)
    trace["citation_count"] = len(response.citations)
    trace["cited_sources"] = len({c.source_id for c in response.citations})
    trace["response_context_count"] = len(response.contexts)
    response.retrieval_diagnostics = trace
    return response


def pack_hybrid_context(candidates: list[FusionCandidate], neighbors: dict[str, list[str]],
                        fact_markdown: str, max_chars: int) -> tuple[list[FusionCandidate], list[str], dict]:
    """Linked rows/headers and parent-neighbor groups must fit as whole units."""
    row_scopes = {(c.binding_id, c.index_revision_id) for c in candidates if (c.metadata or {}).get("row_context")}
    groups: dict[tuple, list[FusionCandidate]] = {}
    for candidate in candidates:
        scope = (candidate.binding_id, candidate.index_revision_id)
        key = scope if scope in row_scopes else (candidate.chunk_id,)
        groups.setdefault(key, []).append(candidate)
    kept, texts, used, dropped = [], [], len(fact_markdown), 0
    if used > max_chars:
        return [], [], {"budget_exceeded": True, "facts_characters": used, "max_context_chars": max_chars}
    for group in groups.values():
        content = list(dict.fromkeys(text for c in group for text in [c.content, *neighbors.get(c.chunk_id, [])]))
        content = [text for text in content if text not in texts]
        size = sum(len(text) + 2 for text in content)
        if used + size > max_chars:
            dropped += len(group)
            continue
        kept.extend(group)
        texts.extend(content)
        used += size
    return kept, texts, {"budget_exceeded": False, "packed_characters": used, "dropped_candidates": dropped,
        "facts_characters": len(fact_markdown), "max_context_chars": max_chars, "atomic_row_groups": len(row_scopes)}
