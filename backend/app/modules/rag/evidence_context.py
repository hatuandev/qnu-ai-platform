"""Compact model projection; raw identity/hash/span objects stay server-side."""

from app.modules.rag.evidence_schemas import EvidenceBlock


def model_block(block: EvidenceBlock) -> dict:
    return {"id": block.id, "source_revision_id": block.source_revision_id, "text": block.text,
            "title": block.title, "page_number": block.page_number, "section": block.section,
            "header_context": block.header_context, "temporal_scope": block.temporal_scope.model_dump(),
            "origin": block.origin, "fact_context": block.fact_context}


def model_context(blocks: list[EvidenceBlock]) -> dict:
    return {"evidence": [model_block(block) for block in blocks],
            "source_context": {block.source_revision_id: block.source_context for block in blocks if block.source_context}}
