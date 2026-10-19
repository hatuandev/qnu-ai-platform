"""One existing ModelOps path, bounded context rounds, atomic proposal staging."""

import asyncio
import json
import time
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.knowledge.services.semantic_binding import (
    ModelSemanticProposal,
    bind_model_proposals,
)
from app.modules.knowledge.services.semantic_context import (
    ContextBuilder,
    SemanticContextPolicy,
    model_context,
)


async def generate_bound_semantics(db: Any, artifact: dict, tenant_id: str, model_name: str | None,
                                   provider_id: str | None, *, document, context_policy=None,
                                   target_table_ids: list[str] | None = None, observer=None) -> dict:
    from app.modules.knowledge.services.semantic_annotations import (
        INSTRUCTION,
        SemanticAnnotations,
        stage_semantic_annotations,
    )
    from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
    from app.modules.modelops.service import modelops_service
    from app.modules.modelops.services.model_catalog_service import model_catalog_service

    policy = context_policy if isinstance(context_policy, SemanticContextPolicy) else SemanticContextPolicy.model_validate(context_policy or {})
    fallback_provider_id, fallback_model_name = None, None
    if not model_name:
        defaults = (await model_catalog_service.get_system_model_defaults(db)).defaults
        model_name, provider_id = defaults.default_chat_model, provider_id or defaults.default_chat_provider_id
        if defaults.default_chat_mode == "combo":
            chain = [item for item in defaults.chat_combo_chain if item.is_active]
            for index, item in enumerate(chain[:-1]):
                if (item.provider_id, item.model_name) == (provider_id, model_name):
                    fallback = chain[index + 1]
                    fallback_provider_id, fallback_model_name = fallback.provider_id, fallback.model_name
                    break
    if not model_name:
        raise AppException("Chưa cấu hình model đọc ngữ nghĩa.", code="SEMANTIC_MODEL_REQUIRED", status_code=422)
    system = INSTRUCTION + json.dumps(ModelSemanticProposal.model_json_schema(), ensure_ascii=False)
    system_bytes = len(system.encode())
    if policy.max_packet_bytes - system_bytes < 2000:
        raise AppException("Ngân sách không đủ cho hợp đồng và ngữ cảnh.", code="SEMANTIC_CONTEXT_BUDGET", status_code=422)
    build_start = time.perf_counter()
    builder = await asyncio.to_thread(ContextBuilder, artifact, document,
        policy.model_copy(update={"max_packet_bytes": policy.max_packet_bytes - system_bytes}))
    packets = await asyncio.to_thread(builder.packets, target_table_ids)
    metrics = {"build_ms": (time.perf_counter() - build_start) * 1000, "calls": 0, "input_utf8_bytes": 0,
               "model_ms": 0.0, "binding_ms": 0.0, "accepted": 0, "rejected": 0, "packet_count": len(packets)}
    if builder.unexamined:
        raise AppException("Có đối tượng vượt ngân sách ngữ cảnh; chưa gửi model hoặc áp dụng dữ liệu.",
            code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422,
            details={"unexamined_unit_ids": sorted(set(builder.unexamined)), "trace": builder.trace, "metrics": metrics})
    minimum_bytes = sum(len(json.dumps(model_context(packet), ensure_ascii=False).encode()) + system_bytes for packet in packets)
    if len(packets) > policy.max_calls or minimum_bytes > policy.max_total_bytes:
        raise AppException("Các gói tối thiểu vượt ngân sách; chưa gọi model hoặc thay đổi dữ liệu.",
            code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422,
            details={"minimum_input_utf8_bytes": minimum_bytes, "metrics": metrics})
    merged = {"notes": [], "cells": [], "limitations": []}
    seen = {key: {} for key in merged}
    runs, unresolved = [], []
    for original in packets:
        packet = original
        while True:
            content = json.dumps(model_context(packet), ensure_ascii=False)
            size = len(content.encode()) + system_bytes
            if metrics["calls"] >= policy.max_calls or metrics["input_utf8_bytes"] + size > policy.max_total_bytes:
                raise AppException("Đã hết ngân sách gọi/mở rộng; dữ liệu hiệu lực giữ nguyên.", code="SEMANTIC_CONTEXT_INCOMPLETE",
                                   status_code=422, details={"metrics": metrics, "trace": builder.trace})
            if observer:
                await observer("context", {"packet": model_context(packet), "call": metrics["calls"] + 1})
            started = time.perf_counter()
            metrics["calls"] += 1
            metrics["input_utf8_bytes"] += size
            response = await modelops_service.generate(db, LLMGenerateRequest(
                tenant_id=tenant_id, preferred_model_name=model_name, preferred_provider_id=provider_id,
                fallback_provider_id=fallback_provider_id, fallback_model_name=fallback_model_name,
                temperature=0, thinking_budget=0, max_tokens=policy.max_output_tokens,
                messages=[ChatMessage(role="system", content=system), ChatMessage(role="user", content=content)]))
            metrics["model_ms"] += (time.perf_counter() - started) * 1000
            model = {"provider": response.provider, "model": response.model, "is_fallback": response.is_fallback,
                     "prompt_tokens": response.prompt_tokens, "completion_tokens": response.completion_tokens, "cost_usd": response.cost_usd}
            runs.append(model)
            if observer:
                await observer("response", {"content": response.content, "model": model, "call": metrics["calls"]})
            started = time.perf_counter()
            try:
                wire = ModelSemanticProposal.model_validate_json(response.content.strip().removeprefix("```json").removesuffix("```").strip())
                if wire.context_id != packet["context_id"]:
                    raise ValueError("EVIDENCE_CONTEXT_MISMATCH")
                if wire.needs_context:
                    packet = await asyncio.to_thread(builder.expand, packet, wire.needs_context)
                    continue
                annotations = await asyncio.to_thread(bind_model_proposals, artifact, packet, wire)
            except (ValueError, KeyError, TypeError) as exc:
                if type(exc) is ValueError and str(exc).startswith("CONTEXT_EXPANSION_"):
                    raise AppException("Chưa đủ ngữ cảnh trong ngân sách; chưa tạo hoặc áp dụng đề xuất.",
                        code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422,
                        details={"stage": "context_expansion", "reason": str(exc), "model": model, "metrics": metrics}) from exc
                metrics["rejected"] += 1
                code = "SEMANTIC_OUTPUT_INVALID" if isinstance(exc, ValidationError) else "SEMANTIC_EVIDENCE_INVALID"
                reason = str(exc) if type(exc) is ValueError else "invalid_selector_schema_or_coordinates"
                raise AppException("Đề xuất không khớp source/span/scope; dữ liệu nháp được giữ nguyên.", code=code, status_code=422,
                                   details={"stage": "binding", "reason": reason[:160], "model": model, "metrics": metrics}) from exc
            finally:
                metrics["binding_ms"] += (time.perf_counter() - started) * 1000
            visible = {unit["id"] for unit in packet["units"]} | {row["id"] for table in packet["tables"] for row in table["rows"]}
            if any(not set(item.unit_ids).issubset(visible) for item in wire.unresolved):
                raise AppException("Báo thiếu căn cứ trỏ sai đối tượng.", code="SEMANTIC_EVIDENCE_INVALID", status_code=422)
            unresolved.extend(item.model_dump() for item in wire.unresolved)
            if packet["deferred_related_unit_ids"]:
                unresolved.append({"unit_ids": packet["deferred_related_unit_ids"],
                    "reason": "Related source units deferred by context budget; semantic support still needs review."})
            for key, entries in merged.items():
                for item in getattr(annotations, key):
                    data = item.model_dump(exclude_none=True)
                    identity = ((item.note_unit_id, item.table_id, item.scope, tuple(item.row_unit_ids), tuple(item.column_ids)) if key == "notes"
                                else (item.row_unit_id, item.column_id))
                    comparison = {k: v for k, v in data.items() if k != "reason"}
                    previous = seen[key].get(identity)
                    if previous is not None and previous != comparison:
                        raise AppException("Hai gói đưa đề xuất xung đột; cần đối soát.", code="SEMANTIC_PROPOSAL_CONFLICT", status_code=422)
                    if previous is None:
                        seen[key][identity] = comparison
                        entries.append(data)
                        metrics["accepted"] += 1
            break
    result = SemanticAnnotations.model_validate(merged)
    review = {"coverage_complete": True, "scope": "document" if target_table_ids is None else "selected_tables",
              "target_table_ids": target_table_ids, "unresolved": unresolved, "expansions": builder.trace,
              "metrics": metrics, "semantic_support": "human_review_required"}
    # The only mutation: stage the entire validated set after all packets succeed.
    return stage_semantic_annotations(artifact, result, model={"runs": runs, "metrics": metrics,
        **(runs[-1] if runs else {})}, context_review=review)
