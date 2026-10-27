"""ModelOps adapter for new-source wiki builds; existing revisions remain unchanged."""

import asyncio
import json
import logging
import re
from itertools import pairwise
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.services.wiki_budget import request_messages, request_usage
from app.modules.knowledge.services.wiki_compiler import (
    Generate,
    compile_wiki,
    digest,
    source_identity,
)
from app.modules.knowledge.services.wiki_transport import prepare_transport, restore_source_ids
from app.modules.knowledge.wiki_schemas import (
    WIKI_VERSION,
    WikiPacketCandidate,
    WikiPacketGeneration,
    WikiPolicy,
)

logger = logging.getLogger(__name__)


def contract_errors(exc: ValidationError, contract: type[BaseModel], reverse: dict, *, span_choices: dict | None=None) -> list[dict]:
    fields = set()
    def visit(node):
        if isinstance(node, dict):
            fields.update(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(contract.model_json_schema())
    result = []
    for error in exc.errors(include_input=True, include_url=False)[:8]:
        location = [part if isinstance(part, int) or part in fields or re.fullmatch(r"(?:page[0-2]|repair[0-8])", str(part))
                    else "[unknown-field]" for part in error["loc"]]
        constraints = {key: value for key, value in (error.get("ctx") or {}).items()
                       if isinstance(value, (int, float, bool))}
        span_feedback={}
        if span_choices is not None:
            from app.modules.knowledge.services.compilation_span_menu import span_error_feedback

            span_feedback=span_error_feedback(error,span_choices)
        result.append({"field": location, "type": error["type"],
            **span_feedback,
            **({"constraints": constraints} if constraints else {}),
            **({"supplied_handle": error["input"]} if isinstance(error.get("input"), str)
               and error["input"] in reverse else {})})
    return result


async def build_revision_wiki(db: Any, source: Any, collection: Any) -> dict | None:
    raw_policy = (source.parse_provenance or {}).get("knowledge_wiki_policy")
    if raw_policy is None:
        return None  # Historical uploads opt in only through a new source revision.
    policy = WikiPolicy.model_validate(raw_policy)
    if not policy.enabled:
        return None
    metrics: list[dict] = []
    try:
        generate = await model_generator(db, collection.tenant_id, policy, metrics)
        bundle = await compile_wiki(source, collection.id, policy, generate)
        bundle["model_calls"] = metrics
        bundle["sha256"] = digest({k: v for k, v in bundle.items() if k != "sha256"})
        return bundle
    except (AppException, ValueError, TimeoutError) as exc:
        # The raw source retains its independent Quality Gate. Failure is visible,
        # and no generated content becomes available for retrieval.
        code = getattr(exc, "code", "KNOWLEDGE_WIKI_CONTRACT_INVALID")
        if isinstance(exc, TimeoutError):
            code = "KNOWLEDGE_WIKI_TIMEOUT"
        logger.warning("knowledge_wiki_unavailable revision=%s code=%s", source.id, code)
        bundle = {"version": WIKI_VERSION, "usage": "navigation_only", "status": "unavailable",
            **source_identity(source, collection.id), "pages": [], "failure_code": code,
            "failure_reason": (getattr(exc, "details", None) or {}).get("reason"),
            "model_calls": metrics, "policy": policy.model_dump()}
        bundle["sha256"] = digest(bundle)
        return bundle


async def model_generator(db: AsyncSession, tenant_id: str, policy: WikiPolicy, metrics: list[dict]) -> Generate:
    from app.modules.modelops.services.model_catalog_service import model_catalog_service

    defaults = (await model_catalog_service.get_system_model_defaults(db)).defaults
    if not defaults.default_chat_model or not defaults.default_chat_provider_id:
        raise AppException("Chưa cấu hình model biên soạn tri thức trong ModelOps.",
                           code="KNOWLEDGE_WIKI_MODEL_REQUIRED", status_code=409)
    route = {"preferred_provider_id": defaults.default_chat_provider_id,
             "preferred_model_name": defaults.default_chat_model}
    if defaults.default_chat_mode == "combo":
        chain = [item for item in defaults.chat_combo_chain if item.is_active]
        for current, following in pairwise(chain):
            if (current.provider_id, current.model_name) == (
                    defaults.default_chat_provider_id, defaults.default_chat_model):
                route.update(fallback_provider_id=following.provider_id,
                             fallback_model_name=following.model_name)
                break

    async def generate(contract: type[BaseModel], instruction: str, payload: dict) -> BaseModel:
        from app.core.database import AsyncSessionFactory

        # Usage/quota auditing may commit. It must not commit the caller's source
        # or chunk-set transaction while an immutable derivative is being built.
        async with AsyncSessionFactory() as inference_db:
            return await generate_object(inference_db, tenant_id, route, policy, metrics, contract, instruction, payload)

    return generate


async def generate_object(db: AsyncSession, tenant_id: str, route: dict, policy: WikiPolicy,
                          metrics: list[dict], contract: type[BaseModel], instruction: str,
                          payload: dict, *, reasoning_effort: str | None = None) -> BaseModel:
    from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
    from app.modules.modelops.service import modelops_service
    from app.modules.modelops.services.inference_policy import preserve_structured_output
    from app.modules.rag.evidence_contracts import validate_data_instance

    budget = await asyncio.to_thread(request_usage, contract, instruction, payload, policy)
    if not budget["fits"]:
        raise AppException("Gói biên soạn vượt ngân sách toàn request; chưa gọi mô hình.",
                           code="KNOWLEDGE_WIKI_BUDGET", status_code=422)
    with preserve_structured_output():
        result = await modelops_service.generate(db, LLMGenerateRequest(tenant_id=tenant_id,
            **route, temperature=0, thinking_budget=0, max_tokens=budget['reserved_output_tokens'], reasoning_effort=reasoning_effort,
            automatic_output_budget=policy.automatic_output_budget,minimum_output_tokens=budget.get('minimum_output_tokens',1),
            messages=[ChatMessage(**message) for message in request_messages(contract, instruction, payload)]))
    budget["observed_input_tokens"] = result.prompt_tokens
    metrics.append({"provider": result.provider, "model": result.model,
        "is_fallback": result.is_fallback, "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens, "request_budget": budget,
        "finish_reason": getattr(result, "finish_reason", None)})
    try:
        content = result.content.strip()
        fence = re.fullmatch(r"```(?:json)?\s*\n?([\s\S]*?)\s*```", content, re.IGNORECASE)
        wire_contract, _, reverse = prepare_transport(contract, payload)
        # A fresh draft can contain a well-formed section with an offered ID
        # belonging to another page. Preserve the draft for section-local repair;
        # compile_wiki still validates every section against its exact outline.
        # Patch contracts stay closed so they cannot alter other sections/pages.
        parse_contract = WikiPacketCandidate if contract is WikiPacketGeneration else wire_contract
        output = validate_data_instance(parse_contract, fence[1] if fence else content)
        return restore_source_ids(parse_contract if contract is WikiPacketGeneration else contract, output, reverse)
    except ValidationError as exc:
        errors = contract_errors(exc, wire_contract, reverse,span_choices=payload.get('source_spans'))
        metrics[-1]["contract_errors"] = errors
        raise AppException("Đầu ra trang tri thức sai cấu trúc.", code="KNOWLEDGE_WIKI_INVALID",
            status_code=502, details={"reason": "json_contract", "validation_errors": errors}) from exc
    except ValueError as exc:
        # Keep parse failures actionable without retaining generated source text
        # or a JSON decoder message containing it in the stored bundle/log.
        reason = "json_syntax" if isinstance(exc, json.JSONDecodeError) else "json_contract"
        errors = [{"field": [], "type": type(exc).__name__}]
        metrics[-1]["contract_errors"] = errors
        raise AppException("Đầu ra trang tri thức không phải JSON hợp lệ.", code="KNOWLEDGE_WIKI_INVALID",
            status_code=502, details={"reason": reason, "validation_errors": errors}) from exc
