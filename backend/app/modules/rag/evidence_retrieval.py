"""Interactive retrieval budgets; degrade only to genuine published evidence."""

import asyncio
import logging

from app.core.database import AsyncSessionFactory
from app.core.evidence_policy import EvidencePolicy
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.reranker import reranker_client
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

logger = logging.getLogger(__name__)


async def retrieve_anchors(req: AskRequest, snapshot: RetrievalSnapshot, query: str,
                           policy: EvidencePolicy, candidate_mode: bool,
                           data_years: list[int] | None = None) -> list[FusionCandidate]:
    try:
        async with asyncio.timeout(policy.retrieval_timeout_seconds):
            # Cancelling slow dense/FTS anchors must not invalidate the parent
            # transaction used to read canonical source spans and reviewed facts.
            async with AsyncSessionFactory() as anchor_db:
                return await hybrid_retriever.retrieve(db=anchor_db, collection_id=req.collection_id,
                    query=query, top_k=12, rerank_top_k=5, tenant_id=req.tenant_id, workspace_id=req.workspace_id,
                    snapshot=snapshot, reranker_policy={**(req.reranker_policy or {}), "enabled": False},
                    data_years=data_years,
                    **({"candidate_mode": True, "read_mode_override": "revisioned"} if candidate_mode else {}))
    except TimeoutError:
        logger.warning("evidence_anchors_timeout snapshot=%s; using published canonical/facts ranking", snapshot.snapshot_id)
        return []


async def bounded_rerank(query: str, candidates: list[FusionCandidate], top_k: int,
                          req: AskRequest, policy: EvidencePolicy) -> list[FusionCandidate]:
    rp = req.reranker_policy or {}
    try:
        async with asyncio.timeout(policy.rerank_timeout_seconds):
            return await reranker_client.rerank(query, candidates, top_k=top_k,
                preferred_provider_id=rp.get("provider_id"), preferred_model_name=rp.get("model_name"),
                score_threshold=rp.get("score_threshold", 0.0))
    except TimeoutError:
        logger.warning("evidence_rerank_timeout provider=%s model=%s; retaining corpus rank", rp.get("provider_id"), rp.get("model_name"))
        return candidates[:top_k]  # No invented CE scores, facts, or embeddings.
