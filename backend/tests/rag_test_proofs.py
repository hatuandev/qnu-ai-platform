"""Literal source doubles for tests of orchestration, not source-verification tests."""

import hashlib

from app.modules.rag.evidence_schemas import EvidenceBlock


async def bind_literal_test_candidates(db, snapshot, candidates, **kwargs):
    result = []
    for candidate in candidates:
        binding = candidate.binding_id or next(iter(snapshot.binding_revisions))
        index = candidate.index_revision_id or snapshot.binding_revisions[binding]
        result.append((candidate, EvidenceBlock(id=candidate.chunk_id, binding_id=binding,
            index_revision_id=index, source_revision_id='unit-source', title='Unit test source',
            text=candidate.content, start=0, end=len(candidate.content),
            canonical_hash=hashlib.sha256(candidate.content.encode()).hexdigest())))
    return result
