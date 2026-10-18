"""Compact model projection; raw identity/hash/span objects stay server-side."""

import json

from app.modules.rag.evidence_schemas import EvidenceBlock


def model_block(block: EvidenceBlock) -> dict:
    return {"id": block.id, "source_revision_id": block.source_revision_id, "text": block.text,
            "title": block.title, "page_number": block.page_number, "section": block.section,
            "header_context": block.header_context, "temporal_scope": block.temporal_scope.model_dump(),
            "origin": block.origin, "fact_context": {key: value for key, value in block.fact_context.items()
                if key not in {"source_locations", "context_unit_ids", "qnu_block_id", "source_unit_id"}},
            "record_label": block.record_label, "record_path": block.record_path,
            "record_heading_id": block.record_heading_id}


def omit_empty_fields(value):
    """Lossless sparse JSON projection; unknown status and zero/false are kept."""
    if isinstance(value, dict):
        return {key: omit_empty_fields(item) for key, item in value.items()
                if item is not None and item != "" and item != [] and item != {}}
    if isinstance(value, list):
        return [omit_empty_fields(item) for item in value]
    return value


def model_context(blocks: list[EvidenceBlock], *, compact: bool = False) -> dict:
    evidence = [model_block(block) for block in blocks]
    return {"evidence": omit_empty_fields(evidence) if compact else evidence,
            "source_context": {block.source_revision_id: block.source_context for block in blocks if block.source_context}}


def compact_claim_context(payload: dict, claims: list[dict]) -> dict:
    """Project repeated bound references once; keep raw proofs server-side.

    Deduplicate by FULL immutable identity before omitting transport-only fields.
    Claim order and primary reference order are unchanged. No source text, scope,
    negation or number is shortened, and unknown temporal status remains explicit.
    """
    catalog, identities, projected = {}, {}, []
    server_fields = {"binding_id", "index_revision_id", "canonical_hash", "start", "end",
                     "source_locations", "source_pages"}
    for claim in claims:
        refs = []
        for reference in claim["references"]:
            identity = json.dumps(reference, sort_keys=True, ensure_ascii=False)
            if identity not in identities:
                key = f"ref{len(catalog)}"
                identities[identity] = key
                catalog[key] = omit_empty_fields({key: value for key, value in reference.items()
                    if key not in server_fields})
            refs.append(identities[identity])
        projected.append({**claim, "references": refs})
    return {**payload, "claims": projected, "reference_catalog": catalog}
