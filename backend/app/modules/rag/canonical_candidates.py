"""Reconcile search excerpts to immutable source units before answer verification."""

from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import Citation, RetrievalSnapshot


async def bind_candidates(db: AsyncSession, snapshot: RetrievalSnapshot, candidates: list[FusionCandidate],
                          *, candidate_mode: bool = False) -> list[tuple[FusionCandidate, EvidenceBlock]]:
    """Search prefixes are not quotes. Missing/ambiguous source mappings remain unusable."""
    blocks = await load_published_blocks(db, snapshot, candidate_mode=candidate_mode)
    result = []
    for candidate in candidates:
        meta = candidate.metadata or {}
        same = [b for b in blocks if b.binding_id == candidate.binding_id and b.index_revision_id == candidate.index_revision_id
                and (not meta.get('source_revision_id') or b.source_revision_id == meta['source_revision_id'])
                and (not meta.get('canonical_hash') or b.canonical_hash == meta['canonical_hash'])]
        unit_id = meta.get('source_unit_id') or (meta.get('source_unit') or {}).get('id')
        if unit_id:
            matches = [b for b in same if b.unit_id == unit_id]
        else:
            matches = [b for b in same if b.text == candidate.content]
        if len(matches) != 1:
            continue
        block = matches[0]
        if block.text not in candidate.content:
            continue  # Do not repair altered OCR or map a fragment to a guessed whole body.
        result.append((replace(candidate, content=block.text), block))
    return result


def canonical_citation(block: EvidenceBlock, source_id: str | None = None) -> Citation:
    return Citation(source_id=source_id or block.binding_id, binding_id=block.binding_id,
        index_revision_id=block.index_revision_id, source_revision_id=block.source_revision_id,
        title=block.title, page_number=block.page_number, quote=block.text,
        canonical_hash=block.canonical_hash, span_start=block.start, span_end=block.end,
        source_locations=block.fact_context.get('source_locations') or None)
