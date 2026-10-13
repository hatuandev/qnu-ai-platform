"""Live FAQ evaluation. No configuration, source, publication or cache changes.

Chat endpoints create their usual conversations, workflow traces and usage.
Expected answers stay local and are never sent to the assistant.
"""

import argparse
import asyncio
import hashlib
import json
import sys
import time
import unicodedata
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def extract_cases(document: Path) -> list[dict]:
    with zipfile.ZipFile(document) as archive:
        body = ET.fromstring(archive.read("word/document.xml"))
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    cases, section, pending = [], "", None
    for paragraph in body.findall(".//w:body/w:p", namespace):
        text = unicodedata.normalize(
            "NFC", "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        ).strip()
        if text.startswith("Hỏi:"):
            if pending is not None:
                raise ValueError("Question without expected answer")
            pending = {"id": len(cases) + 1, "section": section, "question": text[4:].strip()}
        elif text.startswith("Đáp:"):
            if pending is None:
                raise ValueError("Expected answer without question")
            pending["expected_answer"] = text[4:].strip()
            cases.append(pending)
            pending = None
        elif text and text.split(".", 1)[0].strip() in {
            "I",
            "II",
            "III",
            "IV",
            "V",
            "VI",
            "VII",
            "VIII",
            "IX",
            "X",
            "XI",
            "XII",
            "XIII",
            "XIV",
            "XV",
            "XVI",
        }:
            section = text
    if pending is not None:
        raise ValueError("Last question without answer")
    return cases


def save_result(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


async def read_sources(collection_id: str) -> dict:
    from sqlalchemy import select

    from app.core.database import AsyncSessionFactory
    from app.modules.knowledge.models import (
        KnowledgeBinding,
        KnowledgeCollection,
        KnowledgeIndexRevision,
        KnowledgeSourceRevision,
    )

    async with AsyncSessionFactory() as db:
        collection = await db.get(KnowledgeCollection, collection_id)
        bindings = (
            (
                await db.execute(
                    select(KnowledgeBinding).where(
                        KnowledgeBinding.collection_id == collection_id,
                        KnowledgeBinding.status == "active",
                    )
                )
            )
            .scalars()
            .all()
        )
        sources = []
        for binding in bindings:
            source = (
                await db.get(KnowledgeSourceRevision, binding.active_source_revision_id)
                if binding.active_source_revision_id
                else None
            )
            index = (
                await db.get(KnowledgeIndexRevision, binding.active_index_revision_id)
                if binding.active_index_revision_id
                else None
            )
            sources.append(
                {
                    "binding_id": binding.id,
                    "source_revision_id": binding.active_source_revision_id,
                    "index_revision_id": binding.active_index_revision_id,
                    "title": (source.snapshot_metadata or {}).get("title") if source else None,
                    "source_status": source.status if source else None,
                    "index_status": index.status if index else None,
                    "canonical_markdown": source.canonical_markdown if source else None,
                }
            )
        return {
            "collection_id": collection_id,
            "epoch": collection.index_epoch,
            "metadata": collection.collection_metadata,
            "sources": sources,
        }


async def read_trace(execution_id: str) -> list[dict]:
    from sqlalchemy import select

    from app.core.database import AsyncSessionFactory
    from app.modules.workflows.models import WorkflowNodeExecution

    async with AsyncSessionFactory() as db:
        nodes = (
            (
                await db.execute(
                    select(WorkflowNodeExecution).where(
                        WorkflowNodeExecution.execution_id == execution_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "status": node.status,
                "latency_ms": node.latency_ms,
                "output": node.output_data,
            }
            for node in nodes
        ]


async def evaluate(args: argparse.Namespace, cases: list[dict]) -> None:
    import httpx

    path = Path(args.output)
    payload = (
        json.loads(path.read_text(encoding="utf-8"))
        if args.resume and path.exists()
        else {
            "started_at": datetime.now(UTC).isoformat(),
            "document": str(args.document),
            "document_sha256": hashlib.sha256(Path(args.document).read_bytes()).hexdigest(),
            "cases": cases,
            "results": [],
            "method": "independent questions, original text, no expected answer in request",
        }
    )
    async with httpx.AsyncClient(timeout=100, trust_env=False) as client:
        assistant_response = await client.get(args.base + "/assistants/admissions")
        assistant_response.raise_for_status()
        assistant = assistant_response.json()
        payload["assistant"] = {
            key: assistant.get(key)
            for key in (
                "id",
                "code",
                "name",
                "workflow_id",
                "published_workflow_version_id",
                "collection_id",
                "config",
            )
        }
        if "publication" not in payload:
            payload["publication"] = await read_sources(assistant["collection_id"])
        save_result(path, payload)
        print(
            json.dumps(
                {
                    "cases": len(cases),
                    "published_sources": sum(
                        bool(s["index_revision_id"]) for s in payload["publication"]["sources"]
                    ),
                }
            ),
            flush=True,
        )
        semaphore = asyncio.Semaphore(args.concurrency)
        done = {(item["id"], item["route"]) for item in payload["results"]}

        async def run_case(case: dict, route: str) -> None:
            if (case["id"], route) in done:
                return
            async with semaphore:
                started = time.monotonic()
                result = {"id": case["id"], "route": route, "question": case["question"]}
                try:
                    config = assistant.get("config", {})
                    policy = config.get("model_policy", {})
                    body = {
                        "message": case["question"],
                        "conversation_id": f"eval412_{uuid.uuid4().hex[:16]}",
                    }
                    endpoint = "/assistants/admissions/chat"
                    if route == "rag":
                        endpoint = "/rag/ask"
                        body = {
                            "collection_id": assistant["collection_id"],
                            "question": case["question"],
                            "module_code": "admissions",
                            "preferred_model_name": policy.get("primary_model"),
                            "preferred_provider_id": policy.get("primary_provider_id"),
                            "fallback_model": policy.get("fallback_model"),
                            "temperature": policy.get("temperature", 0.2),
                            "max_tokens": policy.get("max_tokens", 1200),
                            "reranker_policy": config.get("knowledge_policy", {}).get(
                                "reranker_policy"
                            ),
                        }
                    response = await client.post(args.base + endpoint, json=body)
                    result.update(http=response.status_code, response=response.json())
                    execution_id = result["response"].get("execution_id")
                    if execution_id:
                        result["trace"] = await read_trace(execution_id)
                except Exception as exc:
                    result["exception"] = {"type": type(exc).__name__, "message": str(exc)}
                result["wall_seconds"] = round(time.monotonic() - started, 2)
                payload["results"].append(result)
                save_result(path, payload)
                response_data = result.get("response", {})
                print(
                    json.dumps(
                        {
                            "id": case["id"],
                            "route": route,
                            "http": result.get("http"),
                            "status": response_data.get("status"),
                            "seconds": result["wall_seconds"],
                            "error": result.get("exception"),
                            "completed": len(payload["results"]),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

        requested_ids = {int(value) for value in args.ids.split(",")} if args.ids else None
        await asyncio.gather(
            *(
                run_case(case, route)
                for case in cases
                if requested_ids is None or case["id"] in requested_ids
                for route in args.routes.split(",")
            )
        )
    payload["finished_at"] = datetime.now(UTC).isoformat()
    save_result(path, payload)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--output", default="storage/admissions_eval412.json")
    parser.add_argument("--base", default="http://localhost:8001/platform/v1alpha1")
    parser.add_argument("--routes", default="dag")
    parser.add_argument("--ids")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    arguments = parser.parse_args()
    extracted = extract_cases(arguments.document)
    if arguments.extract_only:
        print(json.dumps(extracted, ensure_ascii=False, indent=2))
    else:
        asyncio.run(evaluate(arguments, extracted))
