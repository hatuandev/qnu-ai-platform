"""Measure real routing/answer token use against ModelOps capacity; read-only."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from collections import Counter
from datetime import timedelta

from sqlalchemy import select

from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.modelops.capacity.automatic import operational_budget
from qnu.domains.modelops.capacity.service import read_capacity
from qnu.domains.modelops.models import Provider
from qnu.platform.database import AsyncSessionFactory, engine


def _percentile(values: list[float], pct: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return round(ordered[rank - 1], 4)


def _summary(values: list) -> dict:
    clean = [
        float(value)
        for value in values
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    return {
        "samples": len(clean),
        "p50": _percentile(clean, 50),
        "p90": _percentile(clean, 90),
        "max": max(clean) if clean else None,
    }


def _routing_sample(trace: dict) -> dict | None:
    if not isinstance(trace, dict) or "prompt_tokens" not in trace:
        return None
    budget = trace.get("output_budget") or {}
    return {
        "provider_id": trace.get("provider_id"),
        "model_name": trace.get("model_name"),
        "prompt_tokens": trace.get("prompt_tokens"),
        "completion_tokens": trace.get("completion_tokens"),
        "total_tokens": trace.get("total_tokens"),
        "reserved_output_tokens": budget.get("reserved_output_tokens"),
        "sent_output_tokens": budget.get("sent_output_tokens"),
        "budget_mode": budget.get("mode"),
    }


def _answer_sample(result: dict | None) -> dict | None:
    if not isinstance(result, dict) or "trace" not in result:
        return None
    trace = result.get("trace") or {}
    if trace.get("prompt_tokens") is None:
        return None
    contract = trace.get("contract") or {}
    budget = contract.get("output_budget") or {}
    packing = (trace.get("context") or {}).get("packing") or {}
    return {
        "provider_id": trace.get("provider_id"),
        "model_name": trace.get("model_name"),
        "prompt_tokens": trace.get("prompt_tokens"),
        "completion_tokens": trace.get("completion_tokens"),
        "total_tokens": trace.get("total_tokens"),
        "reserved_output_tokens": budget.get("reserved_output_tokens"),
        "sent_output_tokens": budget.get("sent_output_tokens"),
        "budget_mode": budget.get("mode"),
        "request_bytes_estimate": packing.get("request_bytes_estimate"),
        "evidence_envelope_bytes": packing.get("evidence_envelope_bytes"),
        "user_payload_bytes": packing.get("user_payload_bytes"),
    }


def _provider_payload(row: Provider) -> dict:
    capacity = read_capacity(row)
    limits = (
        capacity.token_limits.model_dump(exclude_none=True) if capacity.token_limits else None
    )
    budget = (
        operational_budget(capacity, "chat").model_dump(mode="json")
        if "chat" in (row.capabilities or [])
        else None
    )
    return {
        "provider_id": row.id,
        "model_name": row.model_name,
        "provider_type": row.provider_type,
        "is_active": row.is_active,
        "capacity_status": capacity.status,
        "capacity_basis": capacity.basis,
        "declared_limits": limits,
        "operational_budget": budget,
    }


def _group_rows(stage: str, samples: list[dict], providers: dict) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for sample in samples:
        key = (sample.get("provider_id"), sample.get("model_name"))
        grouped.setdefault(key, []).append(sample)
    fields = [
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reserved_output_tokens",
        "sent_output_tokens",
    ]
    if stage == "answer":
        fields += [
            "request_bytes_estimate",
            "evidence_envelope_bytes",
            "user_payload_bytes",
        ]
    rows = []
    for (provider_id, model_name), items in sorted(
        grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
    ):
        provider = providers.get(provider_id)
        limits = (provider or {}).get("declared_limits") or {}
        input_limit = limits.get("max_input_tokens") or limits.get("context_window_tokens")
        input_basis = (
            "max_input_tokens"
            if limits.get("max_input_tokens")
            else "context_window_tokens"
            if limits.get("context_window_tokens")
            else None
        )
        output_limit = limits.get("max_output_tokens")
        input_shares = [
            item["prompt_tokens"] / input_limit
            for item in items
            if isinstance(item.get("prompt_tokens"), (int, float)) and input_limit
        ]
        output_shares = [
            item["completion_tokens"] / output_limit
            for item in items
            if isinstance(item.get("completion_tokens"), (int, float)) and output_limit
        ]
        row = {
            "provider_id": provider_id,
            "model_name": model_name,
            "capacity_status": provider["capacity_status"] if provider else "provider_missing",
            "declared_limits": limits or None,
            "metrics": {field: _summary([item.get(field) for item in items]) for field in fields},
            "capacity_shares": {
                "input": {
                    "limit": input_limit,
                    "basis": input_basis,
                    **_summary(input_shares),
                },
                "output": {
                    "limit": output_limit,
                    "basis": "max_output_tokens" if output_limit else None,
                    **_summary(output_shares),
                },
            },
            "budget_modes": dict(Counter(item.get("budget_mode") for item in items)),
        }
        rows.append(row)
    return rows


async def build_report(limit: int, days: int | None) -> dict:
    query = select(ConversationTurn).where(ConversationTurn.status == "completed")
    if days:
        query = query.where(ConversationTurn.created_at >= utcnow() - timedelta(days=days))
    query = query.order_by(ConversationTurn.created_at.desc()).limit(limit)
    async with AsyncSessionFactory() as db:
        rows = list((await db.scalars(query)).all())
        routing_samples = []
        answer_samples = []
        direct_replies = 0
        for row in rows:
            trace = row.rewrite_trace or {}
            sample = _routing_sample(trace)
            if sample is not None:
                routing_samples.append(sample)
            if isinstance(row.result, dict) and row.result.get("status") == "direct_reply":
                direct_replies += 1
            answer = _answer_sample(row.result)
            if answer is not None:
                answer_samples.append(answer)
        provider_ids = {
            sample.get("provider_id")
            for sample in routing_samples + answer_samples
            if sample.get("provider_id")
        }
        providers = {}
        if provider_ids:
            provider_rows = (
                await db.scalars(select(Provider).where(Provider.id.in_(provider_ids)))
            ).all()
            providers = {row.id: _provider_payload(row) for row in provider_rows}
    return {
        "schema_version": "qnu.token_budget_report/v1",
        "turns_scanned": len(rows),
        "turns_with_routing": len(routing_samples),
        "turns_with_answers": len(answer_samples),
        "direct_replies": direct_replies,
        "days": days,
        "providers": providers,
        "stages": {
            "routing": _group_rows("routing", routing_samples, providers),
            "answer": _group_rows("answer", answer_samples, providers),
        },
        "notes": [
            "Token counts are provider-reported; *_bytes are UTF-8 JSON estimates.",
            "Capacity shares stay empty when the provider declares no matching limit.",
            "Read-only report; no budget, model or configuration was changed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    async def run() -> dict:
        try:
            return await build_report(args.limit, args.days)
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
