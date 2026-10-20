"""Exact indexed-row anchors and source-bound context, independent of model names."""

import hashlib
import logging
import re
from collections import defaultdict

from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.entity_codes import code_candidates, code_in_question
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_hash_matches,
    resolve_unit_manifest,
)
from app.modules.knowledge.services.source_artifact import (
    get_source_artifact,
    get_structured_review_state,
)
from app.modules.knowledge.services.source_links import build_context_graph, validate_context_graph
from app.modules.knowledge.services.table_context import extract_context_tables
from app.modules.rag.evidence_bm25 import rank_blocks, tokens
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.query_constraints import source_name_in_question
from app.modules.rag.query_router import query_classifier
from app.modules.rag.schemas import RetrievalSnapshot
from app.modules.rag.source_labels import row_identity

logger = logging.getLogger(__name__)


def _key(text: str) -> str:
    return " ".join(term for term in tokens(text) if " " not in term)


def _pages_from_locations(locations: list[dict] | None, fallback: int | None = None) -> list[int]:
    pages = []
    for location in locations or []:
        page = location.get("page") if isinstance(location, dict) else None
        if isinstance(page, int) and not isinstance(page, bool) and page >= 1 and page not in pages:
            pages.append(page)
    if not pages and isinstance(fallback, int) and not isinstance(fallback, bool) and fallback >= 1:
        pages.append(fallback)
    return pages


def _standard_row_fields(artifact: dict, unit, manifest) -> dict:
    """Exact table/row/column identity for standard cell state; legacy stays legacy."""
    if artifact.get("input_format") != "qnu-rag-projection/v1":
        return {}
    for table in artifact.get("tables") or []:
        row_ids = list(table.get("row_unit_ids") or [])
        fields_by_row = table.get("row_fields") or []
        index = row_ids.index(unit.id) if unit.id in row_ids else None
        if index is None:
            # Artifacts created before row_unit_ids keep deterministic row order.
            rows = [row for row in manifest.units if row.parent_id == table.get("id") and row.kind == "table"
                    and not row.is_container and row.text != row.header_context]
            if len(rows) != len(fields_by_row):
                continue
            matches = [position for position, row in enumerate(rows) if row.id == unit.id]
            if not matches:
                continue
            index = matches[0]
        if index >= len(fields_by_row):
            continue
        headers = list(table.get("headers") or [])
        paths = list(table.get("header_paths") or [])
        columns = table.get("columns") or [
            {"id": None, "header_path": paths[position] if position < len(paths) else [header]}
            for position, header in enumerate(headers)]
        return {"row_fields": fields_by_row[index], "row_columns": columns,
                "row_table_id": table.get("id"),
                "cell_state_source": table.get("cell_state_source")}
    return {}


def _matches_row(header: str, text: str, question: str) -> bool:
    if not header or text == header:
        return False
    wanted = " " + _key(question) + " "
    tables = extract_context_tables(header + "\n" + text, 1)
    identities = [identity for table in tables for row in table["rows"]
                  if (identity := row_identity(row, table, question))]
    explicit_codes = code_candidates(question)
    if explicit_codes:
        return any(code and code_in_question(code, question) for _, _, _, code in identities)
    return any((source_name_in_question(name, question) if '_' in name else
                len(_key(name).split()) >= 2 and " " + _key(name) + " " in wanted)
               or code and not re.fullmatch(r"(?:19|20)\d{2}", code)
               and code_in_question(code, question)
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
        pinned_hash = index.parity_report.get("unit_manifest_hash")
        if pinned_hash and not manifest_hash_matches(pinned_hash, manifest):
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
        headers = [by_id[ref] for ref in graph['links'].get(unit.id, [])
                   if by_id[ref].kind == 'table' and by_id[ref].text == unit.header_context]
        # A caption locates its immediately following table; it never supplies a data year.
        if headers:
            preceding = max((item for item in manifest.units if not item.is_container and item.end <= headers[0].start),
                            key=lambda item: item.end, default=None)
            if preceding and re.match(r'^\s*(?:Bảng|Table)\s+(?:\d+|[IVXLCDM]+)\b', preceding.text, re.IGNORECASE):
                context = list({item.id: item for item in [preceding, *context]}.values())
        verified_years = unit.temporal.data_years if unit.temporal.status == "verified" and unit.temporal.role == "data" else []
        table_refs = [unit.id, *graph["links"].get(unit.id, [])]
        fallback_pages = sorted({by_id[ref].page_number for ref in table_refs
                                 if by_id[ref].kind == "table" and isinstance(by_id[ref].page_number, int)})
        row_meta = _standard_row_fields(artifact, unit, manifest)
        metadata.update(source_revision_id=source.id, document_title=source.snapshot_metadata.get("title") or binding.id,
            source_unit_id=unit.id, canonical_hash=source.canonical_hash, data_years=verified_years,
            citation_quote=unit.text, source_locations=list(unit.source_locations),
            source_pages=_pages_from_locations(unit.source_locations, unit.page_number) or fallback_pages,
            row_headers=[by_id[ref].model_dump() for ref in graph["links"].get(unit.id, [])
                         if by_id[ref].kind == "table" and by_id[ref].text == unit.header_context],
            row_context=[{"unit_id": item.id, "text": item.text, "page_number": item.page_number,
                          "source_unit": item.model_dump()} for item in context], **row_meta)
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
    searches += code_candidates(question)
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
            locations = list(item["source_unit"].get("source_locations") or [])
            metadata.update(source_unit_id=item["unit_id"], source_unit=item["source_unit"],
                            citation_quote=item["text"], source_locations=locations,
                            source_pages=_pages_from_locations(locations, item["page_number"]),
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
