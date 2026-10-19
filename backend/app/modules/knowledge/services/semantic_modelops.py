"""One existing ModelOps path, bounded context rounds, atomic proposal staging."""

import asyncio
import copy
import json
import time
from typing import Any

from app.core.exceptions import AppException
from app.modules.knowledge.services.semantic_binding import (
    bind_model_proposals,
)
from app.modules.knowledge.services.semantic_context import (
    ContextBuilder,
    SemanticContextPolicy,
    enforce_packet_budget,
    model_context,
)
from app.modules.knowledge.services.semantic_selector import SelectorError, parse_selector
from app.modules.modelops.services.inference_policy import transient_retry_scope
from app.modules.modelops.services.output_contract import (
    contract_schemas,
    contract_version,
    response_format,
    schema_hash,
)

FORMAT_FEEDBACK = ("The previous response was not one valid JSON object. Return the entire object according to the schema, "
    "without text outside JSON. Keep context_id from this packet and only use IDs supplied in it.")


async def generate_bound_semantics(db: Any, artifact: dict, tenant_id: str, model_name: str | None,
                                   provider_id: str | None, *, document, context_policy=None,
                                   target_table_ids: list[str] | None = None, observer=None) -> dict:
    policy = context_policy if isinstance(context_policy, SemanticContextPolicy) else SemanticContextPolicy.model_validate(context_policy or {})
    with transient_retry_scope(max_input_bytes=policy.max_total_bytes):
        return await _generate_bound_semantics(db, artifact, tenant_id, model_name, provider_id,
            document=document, context_policy=policy, target_table_ids=target_table_ids, observer=observer)


async def _generate_bound_semantics(db: Any, artifact: dict, tenant_id: str, model_name: str | None,
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
    from app.modules.knowledge.services.semantic_run_budget import SemanticRunBudget
    budget = SemanticRunBudget(policy.run_seconds)
    fallback_provider_id, fallback_model_name = None, None
    if not model_name:
        defaults = (await budget.wait(lambda: model_catalog_service.get_system_model_defaults(db))).defaults
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
    contract_name = policy.output_contract.name
    business_schema, wire_schema = contract_schemas(contract_name)
    system = INSTRUCTION + (" For selector v2 choose evidence_id; the backend resolves its owner. Do not send source_unit_id."
        if contract_version(contract_name) == 2 else " For selector v1 source_unit_id must exactly match the evidence owner.")
    system += " Return every schema field explicitly; use [] for empty lists.\n" + json.dumps(wire_schema, ensure_ascii=False)
    system_bytes = len(system.encode())
    contract_bytes = len(json.dumps(response_format({"effective_mode": "json_schema", "name": policy.output_contract.name}), ensure_ascii=False).encode())
    overhead = system_bytes + contract_bytes
    if policy.max_packet_bytes - overhead < 2000:
        raise AppException("Ngân sách không đủ cho hợp đồng và ngữ cảnh.", code="SEMANTIC_CONTEXT_BUDGET", status_code=422)
    build_start = time.perf_counter()
    builder = await budget.wait(lambda: asyncio.to_thread(ContextBuilder, artifact, document,
        policy.model_copy(update={"max_packet_bytes": policy.max_packet_bytes - overhead})))
    packets = await budget.wait(lambda: asyncio.to_thread(builder.packets, target_table_ids))
    metrics = {"build_ms": (time.perf_counter() - build_start) * 1000, "calls": 0, "input_utf8_bytes": 0,
               "model_ms": 0.0, "binding_ms": 0.0, "accepted": 0, "rejected": 0, "packet_count": len(packets),
               "format_retries": 0, "provider_attempts": 0, "transport_attempts": 0, "transport_input_bytes": 0}
    if builder.unexamined:
        raise AppException("Có đối tượng vượt ngân sách ngữ cảnh; chưa gửi model hoặc áp dụng dữ liệu.",
            code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422,
            details={"unexamined_unit_ids": sorted(set(builder.unexamined)), "trace": builder.trace, "metrics": metrics})
    minimum_bytes = sum(len(json.dumps(model_context(packet), ensure_ascii=False).encode()) + overhead for packet in packets)
    if len(packets) > policy.max_calls or minimum_bytes > policy.max_total_bytes:
        raise AppException("Các gói tối thiểu vượt ngân sách; chưa gọi model hoặc thay đổi dữ liệu.",
            code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422,
            details={"minimum_input_utf8_bytes": minimum_bytes, "metrics": metrics})
    merged = {"notes": [], "cells": [], "limitations": []}
    seen = {key: {} for key in merged}
    runs, unresolved, issues, reprocessed = [], [], [], []
    for original in packets:
        packet = original
        format_retries = 0
        feedback = ""
        attempt_history = []
        while True:
            budget.check()
            enforce_packet_budget(packet, builder.policy)
            content = json.dumps(model_context(packet), ensure_ascii=False)
            size = len(content.encode()) + overhead + len(feedback.encode())
            if size > policy.max_packet_bytes:
                raise AppException("Feedback vượt ngân sách gói; chưa áp dụng dữ liệu.", code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422)
            if metrics["calls"] >= policy.max_calls or metrics["input_utf8_bytes"] + size > policy.max_total_bytes:
                raise AppException("Đã hết ngân sách gọi/mở rộng; dữ liệu hiệu lực giữ nguyên.", code="SEMANTIC_CONTEXT_INCOMPLETE",
                                   status_code=422, details={"metrics": metrics, "trace": builder.trace})
            if observer:
                await observer("context", {"packet": model_context(packet), "call": metrics["calls"] + 1})
            started = time.perf_counter()
            metrics["calls"] += 1
            metrics["input_utf8_bytes"] += size
            response = await budget.wait(lambda content=content, feedback=feedback: modelops_service.generate(db, LLMGenerateRequest(
                tenant_id=tenant_id, preferred_model_name=model_name, preferred_provider_id=provider_id,
                fallback_provider_id=fallback_provider_id, fallback_model_name=fallback_model_name,
                output_contract=policy.output_contract,
                temperature=0, thinking_budget=0, max_tokens=policy.max_output_tokens,
                messages=[ChatMessage(role="system", content=system + feedback), ChatMessage(role="user", content=content)])), call_seconds=policy.call_seconds)
            metrics["model_ms"] += (time.perf_counter() - started) * 1000
            model = {"provider": response.provider, "model": response.model, "is_fallback": response.is_fallback,
                     "prompt_tokens": response.prompt_tokens, "completion_tokens": response.completion_tokens, "cost_usd": response.cost_usd,
                     "latency_ms": getattr(response, "latency_ms", None),
                     "output_contract": getattr(response, "output_contract", None), "finish_reason": getattr(response, "finish_reason", None),
                     "response_metadata": getattr(response, "response_metadata", {}), "attempt_trace": getattr(response, "attempt_trace", [])}
            runs.append(model)
            metrics["provider_attempts"] += len(model["attempt_trace"])
            metrics["transport_attempts"] += sum(len(item.get("transport_attempts", [])) for item in model["attempt_trace"])
            metrics["transport_input_bytes"] += sum(attempt.get("request_bytes", 0) for item in model["attempt_trace"] for attempt in item.get("transport_attempts", []))
            packet_trace = {"context_id": packet["context_id"], "packet_sha256": schema_hash(model_context(packet)),
                "source": packet.get("source"), "schema_hash": schema_hash(wire_schema), "business_schema_hash": schema_hash(business_schema),
                "selector_contract": contract_name, "selector_version": contract_version(contract_name),
                "policy": policy.model_dump(mode="json"), "policy_sha256": schema_hash(policy.model_dump(mode="json"))}
            if observer:
                await observer("response", {"content": response.content, "model": model, "call": metrics["calls"], **packet_trace})
            try:
                wire, parse_trace = parse_selector(response, (model["output_contract"] or {}).get("effective_mode", "prompt_only"), expected_contract=contract_name)
            except SelectorError as exc:
                attempt_history.append({**exc.details, **packet_trace, "call": metrics["calls"]})
                if observer:
                    await observer("validation", attempt_history[-1])
                if exc.details["stage"] == "json_syntax" and format_retries < policy.format_retries:
                    format_retries += 1
                    metrics["format_retries"] += 1
                    feedback = "\n" + FORMAT_FEEDBACK
                    continue
                exc.details.update(model=model, metrics=metrics, attempts=attempt_history)
                raise
            if observer:
                await observer("validation", {"stage": "selector_schema", "status": "PASS", **parse_trace, **packet_trace, "call": metrics["calls"]})
            feedback = ""
            started = time.perf_counter()
            try:
                if wire.context_id != packet["context_id"]:
                    raise ValueError("EVIDENCE_CONTEXT_MISMATCH")
                if wire.needs_context:
                    packet = await budget.wait(lambda packet=packet, wire=wire: asyncio.to_thread(builder.expand, packet, wire.needs_context))
                    continue
                annotations = await budget.wait(lambda packet=packet, wire=wire: asyncio.to_thread(bind_model_proposals, artifact, packet, wire,
                    review_issues=issues, selector_contract=contract_name))
            except (ValueError, KeyError, TypeError) as exc:
                if type(exc) is ValueError and str(exc).startswith("CONTEXT_EXPANSION_"):
                    raise AppException("Chưa đủ ngữ cảnh trong ngân sách; chưa tạo hoặc áp dụng đề xuất.",
                        code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422,
                        details={"stage": "context_expansion", "reason": str(exc), "model": model, "metrics": metrics}) from exc
                metrics["rejected"] += 1
                code = "SEMANTIC_EVIDENCE_INVALID"
                reason = str(exc) if isinstance(exc, ValueError) and not hasattr(exc, "errors") else "invalid_selector_schema_or_coordinates"
                diagnostic = {**packet_trace, **parse_trace, "call": metrics["calls"], "stage": "evidence_binding",
                    "reason": reason[:160], "selector": getattr(exc, "diagnostics", None)}
                if observer:
                    await observer("validation", diagnostic)
                raise AppException("Đề xuất không khớp source/span/scope; dữ liệu nháp được giữ nguyên.", code=code, status_code=422,
                                   details={**diagnostic, "model": model, "metrics": metrics, "attempts": attempt_history}) from exc
            finally:
                metrics["binding_ms"] += (time.perf_counter() - started) * 1000
            visible = {unit["id"] for unit in packet["units"]} | {row["id"] for table in packet["tables"] for row in table["rows"]}
            if any(not set(item.unit_ids).issubset(visible) for item in wire.unresolved):
                raise AppException("Báo thiếu căn cứ trỏ sai đối tượng.", code="SEMANTIC_EVIDENCE_INVALID", status_code=422)
            unresolved.extend(item.model_dump() for item in wire.unresolved)
            if wire.context_followups:
                from app.modules.knowledge.services.semantic_context_review import make_issue
                from app.modules.knowledge.services.semantic_evidence import (
                    EvidenceBinding,
                    source_text,
                    verify_binding,
                )
                prior = {item["issue_id"]: item for item in packet["prior_context_issues"]}
                for followup in wire.context_followups:
                    old = prior.get(followup.issue_id)
                    if old is None or old["kind"] not in {"missing_context", "deferred_reference"}:
                        raise AppException("Đề xuất bổ sung trỏ sai issue.", code="SEMANTIC_EVIDENCE_INVALID", status_code=422)
                    source_ids = set()
                    for eid in followup.evidence_ids:
                        if eid not in packet["_bindings"]:
                            raise AppException("Bằng chứng bổ sung ngoài context.", code="SEMANTIC_EVIDENCE_INVALID", status_code=422)
                        binding = EvidenceBinding.model_validate(packet["_bindings"][eid])
                        text = source_text(artifact, binding.source_unit_id, binding.column_id)
                        verify_binding(artifact, binding, text[binding.start:binding.end], binding.source_unit_id)
                        if binding.column_id is not None:
                            raise AppException("Bổ sung điều kiện cần source prose.", code="SEMANTIC_EVIDENCE_INVALID", status_code=422)
                        source_ids.add(binding.source_unit_id)
                    if not source_ids - set(old["unit_ids"]):
                        raise AppException("Chưa có đơn vị nguồn bổ sung cho issue thiếu context.", code="SEMANTIC_CONTEXT_INCOMPLETE", status_code=422)
                    issue = make_issue(artifact, "scope_confirmation_required", sorted(source_ids | set(old["unit_ids"])), old["target"], followup.reason)
                    issues.append(issue)
                    reprocessed.append({"old_issue_id": old["issue_id"], "new_issue_id": issue["issue_id"],
                        "reason": "New source-bound evidence from reprocessing; replacement still requires specific human review."})
            if packet["deferred_related_unit_ids"]:
                from app.modules.knowledge.services.semantic_context_review import make_issue
                for unit_id in packet["deferred_related_unit_ids"]:
                    unit = builder.units[unit_id]
                    if unit.is_container or unit.kind not in {"paragraph", "list", "heading"}:
                        continue
                    issues.append(make_issue(artifact, "deferred_reference", [unit_id],
                        {"table_ids": [table["id"] for table in packet["tables"]]},
                        "Tham chiếu chưa được cấp trong gói; cần đọc và xác nhận không chi phối đích hoặc phân tích lại."))
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
              "issues": issues,
              "reprocessed_issues": reprocessed,
              "metrics": metrics, "semantic_support": "human_review_required"}
    # The only mutation: stage the entire validated set after all packets succeed.
    # A cancelled to_thread may continue; stage only on a private copy, then
    # check the owner deadline again before the single caller-visible mutation.
    staged = copy.deepcopy(artifact)
    pending = await budget.wait(lambda: asyncio.to_thread(stage_semantic_annotations, staged, result,
        model={"runs": runs, "metrics": metrics, **(runs[-1] if runs else {})}, context_review=review))
    budget.check()
    artifact["semantic_annotations"] = staged["semantic_annotations"]
    artifact["review"] = staged["review"]
    if "source_policy" in staged:
        artifact["source_policy"] = staged["source_policy"]
    return pending
