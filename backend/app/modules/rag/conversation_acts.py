"""Deterministic dialogue-act answers over re-verified enumeration records.

No new storage or client-supplied records. Each handler re-derives records
server-side from the current snapshot; scope planning uses configured ModelOps.
Unsupported acts clarify; infrastructure errors remain service errors.
"""

import logging
import re
import unicodedata

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.rag.combination_enumeration import (
    INSTRUCTION as ENUM_INSTRUCTION,
)
from app.modules.rag.combination_enumeration import (
    EnumerationPlan,
    EnumerationScope,
    missing,
    scope_catalog,
    validated_scopes,
)
from app.modules.rag.combination_records import CombinationRecord, clean, query_subjects
from app.modules.rag.evidence_model import structured_call
from app.modules.rag.evidence_runtime import assistant_scope
from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.schemas import AskRequest, AskResponse, Citation, RetrievalSnapshot

logger = logging.getLogger(__name__)

ACT_VERSION = "conversation-act-v1"
MAX_CITED_PROOFS = 8
MAX_CLUSTER_EXAMPLES = 3


def identity_status(code: str, name: str) -> str:
    """Structural readability only: 'listed' or 'broken'.

    Never judges whether a plausible-looking name is factually correct;
    ambiguity is reported separately, never silently fixed or dropped.
    """
    del code
    text = clean(name or "")
    if not text or "\ufffd" in text:
        return "broken"
    if any(unicodedata.category(char).startswith("C") for char in text):
        return "broken"
    alnum = sum(1 for char in text if char.isalnum())
    if alnum < 2 or text.replace(" ", "").isdigit():
        return "broken"
    return "listed"


def identity_key(code: str, name: str) -> tuple[str, str]:
    return clean(code or "").casefold(), clean(name or "").casefold()


def fold_diacritics(text: str) -> str:
    """Structural fold only: strip combining marks, never correct words."""
    return "".join(char for char in unicodedata.normalize("NFD", text)
                   if unicodedata.category(char) != "Mn").casefold()


def effective_year(record: CombinationRecord, scopes: dict[str, EnumerationScope]) -> int | None:
    """Same year rule as the listing renderer: cell year, else validated scope year."""
    row_years = record.years or tuple(record.block.scope_years)
    if len(row_years) == 1:
        return row_years[0]
    if row_years:
        return None
    scope = scopes.get(record.block.source_revision_id)
    return scope.year if scope is not None else None


def summarize_records(records: list[CombinationRecord], scopes: dict[str, EnumerationScope]) -> dict:
    """Count-only rollup; rows keep their own years and sources, never merged."""
    listed = [record for record in records
              if identity_status(record.code, record.name) == "listed"]
    broken = len(records) - len(listed)
    identities: dict[tuple[str, str], dict] = {}
    for record in listed:
        key = identity_key(record.code, record.name)
        identities.setdefault(key, {"code": record.code, "name": record.name})
    by_code: dict[str, set] = {}
    by_name: dict[str, set] = {}
    for key in identities:
        by_code.setdefault(key[0], set()).add(key[1])
        by_name.setdefault(key[1], set()).add(key[0])
    ambiguous = sum(1 for names in by_code.values() if len(names) > 1)
    ambiguous += sum(1 for codes in by_name.values() if len(codes) > 1)
    folded: dict[str, set] = {}
    for key in identities:
        folded.setdefault(fold_diacritics(key[1]), set()).add(key)
    diacritic_variants = 0
    examples = []
    for members in folded.values():
        raw_names = {identities[key]["name"] for key in members}
        if len(members) > 1 and len(raw_names) > 1:
            diacritic_variants += 1
            if len(examples) < MAX_CLUSTER_EXAMPLES:
                examples.append(sorted(raw_names))
    years: dict[int | None, int] = {}
    for record in listed:
        year = effective_year(record, scopes)
        years[year] = years.get(year, 0) + 1
    sources: dict[str, dict] = {}
    for record in listed:
        entry = sources.setdefault(record.block.source_revision_id,
                                   {"title": record.block.title, "records": 0})
        entry["records"] += 1
    return {"records": len(listed), "unique": len(identities), "broken": broken,
            "ambiguous": ambiguous, "diacritic_variants": diacritic_variants,
            "ambiguous_examples": examples, "years": years, "sources": sources}


def _proof_citation(block: EvidenceBlock) -> Citation:
    ref = bind_quote(QuoteReference(block_id=block.id, quote=block.text), {block.id: block})
    return Citation(source_id=block.binding_id, binding_id=block.binding_id,
        index_revision_id=block.index_revision_id, source_revision_id=block.source_revision_id,
        title=block.title, quote=ref["quote"], page_number=block.page_number,
        evidence_origin=block.origin, fact_id=block.fact_id, canonical_hash=block.canonical_hash,
        span_start=ref["start"], span_end=ref["end"])


def _scope_proofs(proofs: dict[str, EvidenceBlock], years: set[int]) -> list[Citation]:
    """Year proofs backing the reported partition, bounded and same-source."""
    picked = []
    for block in proofs.values():
        block_years = {int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", block.text)}
        if block_years.intersection(years):
            picked.append(block)
        if len(picked) >= MAX_CITED_PROOFS:
            break
    return [_proof_citation(block) for block in picked]


def _framing(antecedent: str) -> str:
    short = antecedent.strip().replace("\n", " ")
    if len(short) > 300:
        short = short[:297] + "..."
    return (f'Với câu hỏi "{short}" vừa rồi, mình kiểm tra lại trên kho hiện tại:')


def _coverage_note(summary: dict) -> str:
    parts = [f"Danh sách gồm {summary['unique']} định danh phân biệt được theo mã+tên"]
    if summary["broken"]:
        parts.append(f"không tính {summary['broken']} mục tên chưa đọc được")
    near = summary["ambiguous"] + summary.get("diacritic_variants", 0)
    if near:
        parts.append(f"{near} nhóm mã/tên gần giống nhau được giữ riêng, chưa gộp")
    unknown = summary["years"].get(None, 0)
    if unknown:
        parts.append(f"{unknown} bản ghi chưa rõ năm không dùng cho kết luận theo năm")
    if summary["broken"] or summary["ambiguous"] or summary.get("diacritic_variants") or unknown:
        return "; ".join(parts) + "; không tuyên bố danh sách hoàn chỉnh tuyệt đối."
    return "; ".join(parts) + " trong phạm vi các nguồn đã đối chiếu."


def _year_lines(summary: dict) -> list[str]:
    lines = []
    for year in sorted(year for year in summary["years"] if year is not None):
        lines.append(f"- Năm {year}: {summary['years'][year]} bản ghi.")
    if summary["years"].get(None):
        lines.append(f"- Chưa rõ năm: {summary['years'][None]} bản ghi.")
    return lines


def _clarifier(summary: dict) -> str:
    known = sorted(year for year in summary["years"] if year is not None)
    unknown = summary["years"].get(None, 0)
    if len(known) >= 2 or (unknown and known):
        options = [f"năm {year}" for year in known]
        if unknown:
            options.append("các mục chưa rõ năm")
        return "Bạn muốn xem riêng " + " hay ".join(options) + "?"
    return ""


def render_explanation(antecedent: str, summary: dict, citations: list[Citation]) -> str:
    source_count = len(summary["sources"])
    excerpt_part = f", **{len(citations)}** đoạn trích" if citations else ""
    lines = [_framing(antecedent),
        (f"- Tổng số bản ghi phù hợp: **{summary['records']}** "
         f"(trích từ **{source_count}** tài liệu{excerpt_part})."),
        (f"- Số định danh phân biệt được theo mã+tên: **{summary['unique']}**. "
         "Một ngành có thể xuất hiện ở nhiều nguồn/năm nên số bản ghi lớn hơn số định danh."),
        *_year_lines(summary)]
    if summary["broken"]:
        lines.append(f"- Có {summary['broken']} mục tên chưa đọc được nên không đưa vào danh sách.")
    near = summary["ambiguous"] + summary.get("diacritic_variants", 0)
    if near:
        lines.append(f"- Có {near} nhóm mã/tên gần giống nhau (kể cả khác dấu); giữ riêng từng mục, chưa gộp.")
    lines.append(_coverage_note(summary))
    clarifier = _clarifier(summary)
    if clarifier:
        lines.append(clarifier)
    return "\n".join(lines)


def render_compact(antecedent: str, records: list[CombinationRecord],
                   scopes: dict[str, EnumerationScope], summary: dict) -> str:
    groups: dict[tuple, dict] = {}
    for record in records:
        if identity_status(record.code, record.name) != "listed":
            continue
        year = effective_year(record, scopes)
        key = (year, record.block.source_revision_id if year is None else "", *identity_key(record.code, record.name))
        entry = groups.setdefault(key, {"year": year, "code": record.code, "name": record.name,
                                        "combinations": [], "titles": []})
        for combo in record.combinations:
            if combo not in entry["combinations"]:
                entry["combinations"].append(combo)
        if record.block.title not in entry["titles"]:
            entry["titles"].append(record.block.title)
    lines = [_framing(antecedent), f"Dạng gọn của {summary['records']} bản ghi đã kiểm tra lại:"]
    current_year: object = object()
    ordered = sorted(groups.values(), key=lambda g: (g["year"] or 0, g["code"], g["name"]))
    for entry in ordered:
        if entry["year"] != current_year:
            current_year = entry["year"]
            lines.append(f"Năm {current_year}:" if current_year is not None else "Chưa rõ năm:")
        lines.append(f"- {entry['code'] or '—'} — {entry['name']} "
                     f"({'; '.join(entry['combinations'])}) [{'; '.join(entry['titles'])}]")
    lines.append(_coverage_note(summary))
    return "\n".join(lines)


def _decision(act: str, antecedent: str, summary: dict, snapshot: RetrievalSnapshot,
              status: str, reason: str) -> dict:
    return {"version": ACT_VERSION, "status": status, "reason": reason, "act": act,
        "antecedent_question": antecedent, "recomputed": True,
        "snapshot_id": snapshot.snapshot_id,
        "verified": {"record_count": summary["records"], "unique_identities": summary["unique"],
            "sources": [{"source_revision_id": key, "title": value["title"],
                         "records": value["records"]} for key, value in summary["sources"].items()],
            "years": {str(year) if year is not None else "unknown": count
                      for year, count in summary["years"].items()},
            "quarantined": summary["broken"], "ambiguous_groups": summary["ambiguous"],
            "diacritic_variant_groups": summary.get("diacritic_variants", 0),
            "ambiguous_examples": summary.get("ambiguous_examples", [])},
        "coverage": "recomputed_records_in_current_snapshot"}


async def answer_dialogue_act(db: AsyncSession, req: AskRequest, resolution: dict,
                              *, candidate_snapshot: RetrievalSnapshot | None = None) -> AskResponse | None:
    """Handle explain/reformat/filter turns without a fresh retrieval round.

    Returns None when the previous listing cannot be re-derived so the caller
    asks for clarification. Never replays the old list as an explanation.
    """
    try:
        return await _handle_act(db, req, resolution, candidate_snapshot)
    except AppException:
        raise
    except Exception as exc:
        raise AppException("Không thể đối soát lại kết quả hội thoại.",
                           code="CONVERSATION_ACT_UNAVAILABLE", status_code=503) from exc


async def resolve_act_scopes(db: AsyncSession, scoped: AskRequest, subjects: list[str],
                             records: list[CombinationRecord], proofs: dict[str, EvidenceBlock],
                             snapshot: RetrievalSnapshot) -> dict[str, EnumerationScope]:
    """Recompute and validate current scopes; do not conceal provider failures."""
    catalog = scope_catalog(records, proofs)
    try:
        plan = await structured_call(db, scoped, EnumerationPlan, ENUM_INSTRUCTION,
            {"question": scoped.question, "assistant_scope": assistant_scope(scoped),
             "subjects": subjects, "sources": catalog}, max_tokens=1600)
        return validated_scopes(plan, catalog, proofs, scoped.question)
    except ValueError as exc:
        raise AppException("Chưa xác minh được phạm vi của kết quả hội thoại.",
                           code="CONVERSATION_SCOPE_INVALID", status_code=422) from exc


async def _handle_act(db: AsyncSession, req: AskRequest, resolution: dict,
                      candidate_snapshot: RetrievalSnapshot | None) -> AskResponse | None:
    from app.modules.rag.combination_enumeration import load_records
    from app.modules.rag.retriever import hybrid_retriever

    mode = (resolution or {}).get("mode")
    antecedent = ((resolution or {}).get("antecedent_question") or "").strip()
    if mode not in ("explain", "reformat", "filter") or not antecedent:
        return None
    if candidate_snapshot is not None and (
            (candidate_snapshot.collection_id != req.collection_id)):
        logger.warning("conversation_act_foreign_snapshot mode=%s", mode)
        return None
    subjects = query_subjects(antecedent)
    if not subjects:
        return None
    snapshot = candidate_snapshot or await hybrid_retriever.resolve_retrieval_snapshot(
        db, req.collection_id, pinned_snapshot=req.retrieval_snapshot or getattr(req, "snapshot", None),
        tenant_id=req.tenant_id, workspace_id=req.workspace_id)
    scoped = req.model_copy(update={"question": antecedent})
    records, proofs = await load_records(db, scoped, snapshot, subjects,
        candidate_snapshot is not None)
    if not records:
        return None
    scopes = await resolve_act_scopes(db, scoped, subjects, records, proofs, snapshot)
    if mode in ("explain", "reformat"):
        requested_years = {int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", antecedent)}
        if requested_years:
            records = [record for record in records if effective_year(record, scopes) in requested_years]
        if not records:
            return missing(snapshot, "NO_MATCHING_RECORDS")
    summary = summarize_records(records, scopes)
    if mode == "explain":
        years = {year for year in summary["years"] if year is not None}
        citations = _scope_proofs(proofs, years)
        answer = render_explanation(antecedent, summary, citations)
        return AskResponse(status="answered", answer=answer, answer_format="paragraph",
            citations=citations, retrieval_snapshot=snapshot, snapshot=snapshot,
            answer_decision=_decision(mode, antecedent, summary, snapshot, "supported", "RECOMPUTED_EXPLANATION"))
    if mode == "reformat":
        citations = [_proof_citation(record.block) for record in records
                     if identity_status(record.code, record.name) == "listed"]
        seen: dict[tuple, Citation] = {}
        for citation in citations:
            seen.setdefault((citation.binding_id, citation.index_revision_id, citation.source_revision_id,
                             citation.span_start, citation.span_end, citation.fact_id, citation.quote), citation)
        answer = render_compact(antecedent, records, scopes, summary)
        return AskResponse(status="answered", answer=answer, answer_format="paragraph",
            citations=list(seen.values()), retrieval_snapshot=snapshot, snapshot=snapshot,
            answer_decision=_decision(mode, antecedent, summary, snapshot, "supported", "RECOMPUTED_REFORMAT"))
    years = {int(year) for year in (resolution.get("years") or [])}
    if not years:
        return None
    kept = [record for record in records
            if effective_year(record, scopes) in years
            and identity_status(record.code, record.name) == "listed"]
    if not kept:
        return missing(snapshot, "NO_MATCHING_RECORDS")
    from app.modules.rag.combination_enumeration import render_records
    response = render_records(kept, scopes, proofs, snapshot, requested_years=years)
    dropped = summary["records"] - len(kept)
    note = (f"Với câu hỏi \"{antecedent[:300]}\" vừa rồi, mình kiểm tra lại trên kho hiện tại "
            f"và chỉ giữ các bản ghi năm {', '.join(map(str, sorted(years)))}.")
    if dropped:
        note += f" Không gồm {dropped} bản ghi ngoài phạm vi năm hoặc tên chưa đọc được."
    response.answer = note + "\n\n" + response.answer
    decision = response.answer_decision or {}
    decision.update({"act": mode, "antecedent_question": antecedent, "recomputed": True,
                     "filtered_years": sorted(years)})
    response.answer_decision = decision
    return response
