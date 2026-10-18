"""Opt-in single-question acceptance probe; fixed internal-only egress boundary."""

import argparse
import asyncio
import json
import logging
import re
import sys
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionFactory, engine
from app.core.exceptions import AppException
from app.modules.assistants.runtime import build_runtime_profile
from app.modules.assistants.service import assistant_service
from app.modules.rag.evidence_blocks import load_published_blocks, rank_blocks, section_neighbors
from app.modules.rag.prose_selection import topic_order
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service


async def main(args):
    if not args.live and not args.inspect:
        raise SystemExit("Use --live to permit one internal-only inference request.")
    logging.disable(logging.CRITICAL)
    original_send = httpx.AsyncClient.send
    provider_id = "prov_rtx5090_vllm"
    qdrant = httpx.URL(settings.QDRANT_URL)

    async def internal_send(client, request, *a, **kw):
        readonly_qdrant = ((request.url.scheme, request.url.host, request.url.port) ==
            (qdrant.scheme, qdrant.host, qdrant.port) and request.url.path.startswith("/collections")
            and (request.method == "GET" or (request.method == "POST" and
                 request.url.path.endswith(("/query", "/search")))))
        if request.url.host != "100.105.13.53" and not readonly_qdrant:
            raise RuntimeError("INTERNAL_DIAGNOSTIC_EGRESS_BLOCKED")
        if request.url.path.endswith("/chat/completions"):
            data = json.loads(request.content)
            print(json.dumps({"request_characters": sum(len(m["content"]) for m in data.get("messages", [])),
                              "max_tokens": data.get("max_tokens")}), flush=True)
        response = await original_send(client, request, *a, **kw)
        if response.status_code == 400:
            body = response.json()
            message = (body.get("error") or {}).get("message", "")
            counts = re.findall(r"\d+(?= (?:input )?tokens)", message)
            print(json.dumps({"upstream_400_token_counts": counts}), flush=True)
        return response

    try:
        async with AsyncSessionFactory() as db:
            base = (await db.execute(text("SELECT api_base_url FROM model_provider_configs WHERE id=:id"),
                                     {"id": provider_id})).scalar_one()
            if urlsplit(base).hostname != "100.105.13.53":
                raise RuntimeError("INTERNAL_PROVIDER_ENDPOINT_CHANGED")
            assistant = await assistant_service.get_assistant(db, args.assistant)
            profile = build_runtime_profile(assistant)
            model = profile.model_policy
            if model.preferred_provider_id != provider_id:
                raise RuntimeError("SAVED_PRIMARY_NOT_INTERNAL_NO_PROBE_RUN")
            req = AskRequest(question=args.question, collection_id=profile.collection_id,
                assistant_code=assistant.code, assistant_revision=profile.assistant_revision,
                runtime_policy=profile.model_dump(mode="json"), system_prompt=profile.system_prompt,
                max_tokens=model.max_tokens, temperature=model.temperature,
                preferred_provider_id=provider_id, preferred_model_name=model.primary_model,
                fallback_model=None, fallback_provider_id=None,
                reranker_policy=profile.knowledge_policy.reranker_policy.model_dump(mode="json"))
            if args.inspect:
                snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, req.collection_id,
                    tenant_id=req.tenant_id, workspace_id=req.workspace_id)
                blocks = await load_published_blocks(db, snapshot)
                ranked = rank_blocks(blocks, [args.topic], len(blocks))
                ranked = topic_order(ranked, [args.topic])
                print(json.dumps({"sections": [{"id": b.id, "length": len(b.text)} for b in section_neighbors(blocks, args.topic, [], 10)], "count": len(blocks), "ranked": [
                    {"rank": i, "id": b.id, "kind": b.fact_context.get("source_kind"),
                     "container": b.is_container, "characters": len(b.text)}
                    for i, b in enumerate(ranked, 1)][:15]}, ensure_ascii=True), flush=True)
                await db.rollback()
                return
            with (patch("app.modules.modelops.services.inference_policy.load_rag_provider_ids",
                        AsyncMock(return_value=frozenset({provider_id}))),
                  patch("app.modules.rag.service.semantic_cache.get", AsyncMock(return_value=None)),
                  patch("app.modules.rag.service.semantic_cache.set", AsyncMock()),
                  patch.object(httpx.AsyncClient, "send", internal_send)):
                try:
                    async with asyncio.timeout(120):
                        result = await rag_service.ask(db, req)
                    print(json.dumps({"status": result.status, "answer": result.answer,
                        "citation_count": len(result.citations),
                        "citations": [{"binding": c.binding_id, "revision": c.source_revision_id,
                                       "page": c.page_number} for c in result.citations],
                        "reason": (result.answer_decision or {}).get("reason"),
                        "diagnostics": result.retrieval_diagnostics}, ensure_ascii=True), flush=True)
                except AppException as exc:
                    print(json.dumps({"code": exc.code, "details": exc.details,
                                      "diagnostics": req._retrieval_diagnostics}, ensure_ascii=True), flush=True)
                except TimeoutError:
                    print(json.dumps({"code": "DIAGNOSTIC_TIMEOUT"}), flush=True)
            await db.rollback()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--assistant", default="admissions")
    parser.add_argument("--question", required=True)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--topic", default="")
    asyncio.run(main(parser.parse_args()))
