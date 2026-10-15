"""Exact indexed-row anchors and source-bound context, independent of model names."""

import hashlib
import logging
import re
from collections import defaultdict

from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_digest,
    resolve_unit_manifest,
)
from app.modules.knowledge.services.source_artifact import (
    get_source_artifact,
    get_structured_review_state,
)
from app.modules.knowledge.services.source_links import build_context_graph, validate_context_graph
from app.modules.knowledge.services.table_context import extract_context_tables, row_identities
from app.modules.rag.evidence_bm25 import rank_blocks, tokens
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.query_router import query_classifier
from app.modules.rag.schemas import RetrievalSnapshot

logger = logging.getLogger(__name__)


def _key(text: str) -> str:
    return " ".join(term for term in tokens(text) if " " not in term)


def _matches_row(header: str, text: str, question: str) -> bool:
    if not header or text == header:
        return False
    wanted = " " + _key(question) + " "
    tables = extract_context_tables(header + "\n" + text, 1)
    identities = [identity for table in tables for row in table["rows"] for identity in row_identities(row, table)]
    return any((len(_key(name).split()) >= 2 and " " + _key(name) + " " in wanted)
               or code and not re.fullmatch(r"(?:19|20)\d{2}", code)
               and re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", question)
               for _, _, name, code in identities)


def source_rows(source: KnowledgeSourceRevision, index: KnowledgeIndexRevision,
                binding: KnowledgeBinding, chunks: list[KnowledgeChunk], question: str) -> list[FusionCandidate]:
    """Find complete entity cells, never matches in subject-combination/value cells."""
    markdown = source.canonical_markdown or ""
    try:
        if (hashlib.sha256(markdown.encode("utf-8")).hexdigest() != source.canonical_hash
                or get_structured_review_state(source)[1] or not index.parity_report.get("parity_passed")):
            raise ValueError("Source hash/review/parity mismatch")
        artifact = get_source_artifact(source)
        manifest = resolve_unit_manifest(markdown, artifact)
        if index.parity_report.get("unit_manifest_hash", manifest_digest(manifest)) != manifest_digest(manifest):
            raise ValueError("Source/index manifest mismatch")
        graph = artifact.get("context_graph") or build_context_graph(manifest)
        validate_context_graph(graph, manifest)
    except (TypeError, ValueError) as exc:
        raise AppException("Hàng bảng không khớp bản nguồn đã xuất bản.", code="SOURCE_ROW_INVALID", status_code=503) from exc
    by_id = {unit.id: unit for unit in manifest.units}
    result = []
    for chunk in chunks:
        if chunk.binding_id != binding.id or chunk.index_revision_id != index.id:
            continue
        metadata = dict(chunk.chunk_metadata or {})
        unit = by_id.get(metadata.get("source_unit_id"))
        if not unit or unit.kind != "table" or unit.is_container or unit.text == unit.header_context:
            continue
        if not _matches_row(unit.header_context, unit.text, question):
            continue
        if unit.text not in chunk.content:
            raise AppException("Nội dung hàng không khớp chunk đã xuất bản.", code="SOURCE_ROW_INVALID", status_code=503)
        context = [by_id[ref] for ref in graph["links"].get(unit.id, []) if by_id[ref].kind != "table"]
        verified_years = unit.temporal.data_years if unit.temporal.status == "verified" and unit.temporal.role == "data" else []
        metadata.update(source_revision_id=source.id, document_title=source.snapshot_metadata.get("title") or binding.id,
            source_unit_id=unit.id, canonical_hash=source.canonical_hash, data_years=verified_years,
            citation_quote=unit.text,
            row_headers=[by_id[ref].model_dump() for ref in graph["links"].get(unit.id, [])
                         if by_id[ref].kind == "table" and by_id[ref].text == unit.header_context],
            source_pages=sorted({by_id[ref].page_number for ref in [unit.id, *graph["links"].get(unit.id, [])]
                                 if by_id[ref].kind == "table" and isinstance(by_id[ref].page_number, int)}),
            row_context=[{"unit_id": item.id, "text": item.text, "page_number": item.page_number,
                          "source_unit": item.model_dump()} for item in context])
        result.append(FusionCandidate(chunk_id=chunk.id, document_id=binding.id, content=chunk.content,
            rrf_score=0.0, page_number=unit.page_number, section=chunk.section,
            binding_id=binding.id, index_revision_id=index.id, metadata=metadata))
    return result


def rank_row_anchors(rows: list[FusionCandidate], question: str, limit: int = 6) -> list[FusionCandidate]:
    """BM25 over raw row + linked scope; years are hints, never issue-year promotion."""
    blocks = [EvidenceBlock(id=row.chunk_id, binding_id=row.binding_id, index_revision_id=row.index_revision_id,
        source_revision_id=row.metadata["source_revision_id"], title=row.metadata["document_title"],
        text=row.content + "\n" + "\n".join(item["text"] for item in row.metadata["row_context"]),
        start=0, end=len(row.content), scope_years=row.metadata["data_years"]) for row in rows]
    by_id = {row.chunk_id: row for row in rows}
    years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", question)]
    return [by_id[block.id] for block in rank_blocks(blocks, [question], limit, years)]


async def load_row_anchors(db: AsyncSession, snapshot: RetrievalSnapshot, question: str,
                           *, candidate_mode: bool = False) -> list[FusionCandidate]:
    if not snapshot.tenant_id or not snapshot.workspace_id or not snapshot.binding_revisions:
        return []
    # Structural n-grams find new entity names without a handwritten catalog or
    # relying on the query classifier recognizing a particular numeric metric.
    words = re.findall(r"[^\W\d_]+", question.casefold())
    analysis = query_classifier.analyze(question)
    searches = [name for name in analysis.target_entities if len(name.split()) >= 2]
    searches += re.findall(r"\b\d{7}\b", question)
    if not searches:
        searches = [" ".join(words[i:i + 2]) for i in range(len(words) - 1)]
    terms = [func.to_tsvector(literal_column("'simple'::regconfig"), KnowledgeChunk.content).op("@@")(
        func.plainto_tsquery(literal_column("'simple'::regconfig"), name)) for name in searches]
    if not terms:
        return []
    query = (select(KnowledgeChunk, KnowledgeSourceRevision, KnowledgeIndexRevision, KnowledgeBinding)
        .join(KnowledgeIndexRevision, KnowledgeChunk.index_revision_id == KnowledgeIndexRevision.id)
        .join(KnowledgeBinding, KnowledgeChunk.binding_id == KnowledgeBinding.id)
        .join(KnowledgeSourceRevision, KnowledgeIndexRevision.source_revision_v2_id == KnowledgeSourceRevision.id)
        .join(KnowledgeCollection, KnowledgeChunk.collection_id == KnowledgeCollection.id)
        .where(KnowledgeChunk.collection_id == snapshot.collection_id,
            KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values()),
            KnowledgeIndexRevision.binding_id == KnowledgeBinding.id,
            KnowledgeSourceRevision.binding_id == KnowledgeBinding.id,
            KnowledgeBinding.collection_id == snapshot.collection_id, KnowledgeBinding.status == "active",
            KnowledgeIndexRevision.status.in_(["active", "ready"] if candidate_mode else ["active"]),
            KnowledgeSourceRevision.status == "ready",


            KnowledgeChunk.chunk_metadata["source_unit"]["kind"].astext == "table", or_(*terms)))
    try:
        records = (await db.execute(query)).all()
    except Exception as exc:
        raise AppException("Không thể tra cứu hàng bảng đã xuất bản.", code="SOURCE_ROW_UNAVAILABLE", status_code=503) from exc
    grouped = defaultdict(list)
    sources = {}
    for chunk, source, index, binding in records:
        raw_unit = (chunk.chunk_metadata or {}).get("source_unit") or {}
        matches = _matches_row(raw_unit.get("header_context", ""), raw_unit.get("text", ""), question)
        if snapshot.binding_revisions.get(binding.id) == index.id and matches:
            grouped[index.id].append(chunk)
            sources[index.id] = (source, index, binding)
    rows = [row for key, chunks in grouped.items() for row in source_rows(*sources[key], chunks, question)]
    selected = rank_row_anchors(rows, question)
    logger.info("source_row_anchors snapshot=%s matched=%d selected=%d", snapshot.snapshot_id, len(rows), len(selected))
    return selected


def merge_row_anchors(candidates: list[FusionCandidate], rows: list[FusionCandidate], limit: int) -> list[FusionCandidate]:
    """Reserve exact entity anchors and whole linked units; do not invent CE scores."""
    if not rows:
        return candidates
    by_chunk = {row.chunk_id: row for row in rows[:2]}
    for candidate in candidates:
        by_chunk.setdefault(candidate.chunk_id, candidate)
    selected = list(by_chunk.values())[:max(2, limit)]
    context = []
    for row in rows[:2]:
        for item in row.metadata["row_context"]:
            metadata = {key: value for key, value in row.metadata.items() if key != "row_context"}
            scope = item["source_unit"]["temporal"]
            metadata.update(source_unit_id=item["unit_id"], source_unit=item["source_unit"],
                            citation_quote=item["text"], source_pages=[item["page_number"]] if item["page_number"] else [],
                            data_years=scope["data_years"] if scope["status"] == "verified" and scope["role"] == "data" else [],
                            context_only=True)
            context.append(FusionCandidate(chunk_id=row.metadata["source_revision_id"] + ":" + item["unit_id"],
                document_id=row.document_id, content=item["text"], rrf_score=0.0, page_number=item["page_number"],
                binding_id=row.binding_id, index_revision_id=row.index_revision_id, metadata=metadata))
    unique = {}
    for candidate in [*selected, *context]:
        meta = candidate.metadata or {}
        key = (candidate.binding_id, candidate.index_revision_id, meta.get("source_unit_id") or candidate.chunk_id)
        unique.setdefault(key, candidate)
    return list(unique.values())
