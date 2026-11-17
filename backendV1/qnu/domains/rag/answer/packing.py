"""Trim retrieved evidence against the exact envelope sent to the model."""

import json

from qnu.domains.rag.answer.cells import catalog
from qnu.domains.rag.answer.coverage import plan_for
from qnu.domains.rag.answer.drafting import messages_for
from qnu.domains.rag.answer.selection import question_needs
from qnu.domains.rag.answer.table_selection import (
    requested_data_years,
    requested_intakes,
    select_catalog,
)
from qnu.platform.errors import AppException

MANDATORY_ADDED_KINDS = frozenset({"clause"})


def _anchor_rank(context: dict):
    """Rank optional reading by its anchor's retrieval order, not by list position."""
    primary_rank = {
        chunk_id: rank for rank, chunk_id in enumerate(context.get("primary_ids") or [])
    }
    anchors = {
        item["chunk_id"]: item.get("primary_chunk_id")
        for item in context.get("added") or []
    }
    outside = len(primary_rank)
    return lambda chunk_id: primary_rank.get(anchors.get(chunk_id), outside)


def pack_messages(req, sources, context, **options):
    """Trim added reading context; clause and table support stay mandatory."""
    optional = {
        item["chunk_id"]
        for item in context.get("added", [])
        if item.get("kind") not in MANDATORY_ADDED_KINDS
    }
    rank = _anchor_rank(context)
    skipped = []
    include_names = question_needs(req.question)["enumeration"]
    while True:
        cells = catalog(sources, context.get("table_links"), include_names=include_names)
        cells = select_catalog(
            cells,
            sources,
            options.get("resolved_question") or req.question,
            context.get("table_links", []),
            data_years=requested_data_years(options.get("metadata_filter")),
            intakes=requested_intakes(options.get("metadata_filter")),
        )
        messages = messages_for(
            req.question,
            sources,
            table_context=context.get("table_links"),
            table_cells=cells,
            answer_plan=plan_for(sources, context),
            **options,
        )
        envelope = json.loads(messages[-1].content)
        evidence = {
            key: envelope[key]
            for key in ("evidence", "tables", "unselectable", "reading", "joins", "plan")
            if key in envelope
        }
        size = len(json.dumps(evidence, ensure_ascii=False, separators=(",", ":")).encode())
        if size <= req.context_max_bytes:
            return messages, cells, evidence, size, skipped
        trimmable = [index for index, source in enumerate(sources) if source.chunk_id in optional]
        if not sources or not trimmable:
            raise AppException(
                "Bằng chứng bắt buộc vượt ngân sách context.",
                code="answer_context_budget_exceeded",
                status_code=422,
            )
        worst = max(trimmable, key=lambda index: (rank(sources[index].chunk_id), index))
        skipped.append(sources.pop(worst).chunk_id)
