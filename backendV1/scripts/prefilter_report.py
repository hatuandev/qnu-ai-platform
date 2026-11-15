"""Summarize shadow prefilter verdicts against the authoritative router route."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import timedelta

from sqlalchemy import select

from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import AsyncSessionFactory, engine


async def build_report(limit: int, days: int | None, show_questions: bool) -> dict:
    query = select(ConversationTurn).where(ConversationTurn.rewrite_trace.isnot(None))
    if days:
        query = query.where(ConversationTurn.created_at >= utcnow() - timedelta(days=days))
    query = query.order_by(ConversationTurn.created_at.desc()).limit(limit)
    async with AsyncSessionFactory() as db:
        rows = list((await db.scalars(query)).all())
    verdicts: Counter[str] = Counter()
    routes: Counter[str] = Counter()
    compared = agreed = 0
    avoidable = 0
    knowledge_compared = knowledge_agreed = 0
    mismatches = []
    for row in rows:
        prefilter = (row.rewrite_trace or {}).get("prefilter")
        if not isinstance(prefilter, dict):
            continue
        verdict = prefilter.get("verdict", "unknown")
        verdicts[verdict] += 1
        if verdict == "knowledge" and prefilter.get("confidence") == "high":
            avoidable += 1
        route = prefilter.get("router_route")
        if route is None:
            continue
        routes[route] += 1
        compared += 1
        agreement = prefilter.get("agreement")
        if agreement:
            agreed += 1
        if verdict == "knowledge":
            knowledge_compared += 1
            knowledge_agreed += int(bool(agreement))
        if agreement is False:
            item = {"turn_id": row.id, "verdict": verdict, "route": route}
            if show_questions:
                item["question"] = row.question
            mismatches.append(item)
    return {
        "schema_version": "qnu.conversation.prefilter_report/v1",
        "turns_scanned": len(rows),
        "verdicts": dict(verdicts),
        "compared": compared,
        "agreements": agreed,
        "agreement_rate": round(agreed / compared, 4) if compared else None,
        "knowledge_precision": (
            round(knowledge_agreed / knowledge_compared, 4) if knowledge_compared else None
        ),
        "router_calls_shadow_avoidable": avoidable,
        "routes": dict(routes),
        "mismatches": mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--show-questions", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    async def run() -> dict:
        try:
            return await build_report(args.limit, args.days, args.show_questions)
        finally:
            await engine.dispose()

    report = asyncio.run(run())
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as file:
            file.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
