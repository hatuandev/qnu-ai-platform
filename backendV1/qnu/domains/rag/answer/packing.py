"""Trim retrieved evidence against the exact envelope sent to the model."""

import json

from qnu.domains.rag.answer.cells import catalog
from qnu.domains.rag.answer.coverage import plan_for
from qnu.domains.rag.answer.drafting import messages_for
from qnu.domains.rag.answer.table_selection import select_catalog
from qnu.platform.errors import AppException


def pack_messages(req, sources, context, **options):
    """Trim optional neighbors against the actual evidence envelope."""
    optional = {
        item["chunk_id"]
        for item in context.get("added", [])
        if item.get("kind") not in {"clause", "structure"}
    }
    skipped = []
    while True:
        cells = catalog(sources, context.get("table_links"))
        cells = select_catalog(
            cells,
            sources,
            options.get("resolved_question") or req.question,
            context.get("table_links", []),
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
            for key in ("evidence", "tables", "unselectable", "reading", "plan")
            if key in envelope
        }
        size = len(json.dumps(evidence, ensure_ascii=False, separators=(",", ":")).encode())
        if size <= req.context_max_bytes:
            return messages, cells, evidence, size, skipped
        if not sources or sources[-1].chunk_id not in optional:
            raise AppException(
                "Bằng chứng bắt buộc vượt ngân sách context.",
                code="answer_context_budget_exceeded",
                status_code=422,
            )
        skipped.append(sources.pop().chunk_id)
