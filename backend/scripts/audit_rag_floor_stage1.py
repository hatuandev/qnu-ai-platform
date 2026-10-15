"""Stage-one diagnosis only: inspect published data and trace two genuine chats.

Default is read-only inspection (plus local JSON/PNG artifacts). --live invokes
the same assistant service as the API, with fresh conversations and REAL models.
That option creates ordinary conversation/usage/gap records; it never publishes,
reindexes, changes policy, seeds, deletes, or repairs application data. Wrappers
record original calls/results without replacing any dependency with fake output.
Run from backend: python -m scripts.audit_rag_floor_stage1 --output storage/rag_stage1_466
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from contextlib import ExitStack
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pymupdf
from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.service import assistant_service
from app.modules.rag.query_router import query_classifier
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.vector_indexer import vector_indexer

CASES = [
    {"id": "management", "code": "7140114", "question": "Điểm sàn ngành Quản lý giáo dục năm 2026 là bao nhiêu?"},
    {"id": "mathematics", "code": "7140209", "question": "Điểm sàn ngành Sư phạm Toán học năm 2026 là bao nhiêu?"},
]


def serializable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return serializable(asdict(value))
    if isinstance(value, dict):
        return {str(key): serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serializable(item) for item in value]
    if value is None or isinstance(value, (str, float, bool, int)):
        return value
    # Facts are ORM instances, serialize only public evidence fields.
    if hasattr(value, "entity_name"):
        return {key: serializable(getattr(value, key, None)) for key in (
            "id", "entity_name", "entity_code", "attribute_name", "attribute_value",
            "attribute_code", "applicability_year", "binding_id", "index_revision_id", "raw_data")}
    return str(value)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(serializable(value), sort_keys=True,
                                    ensure_ascii=False).encode("utf-8")).hexdigest()


def runtime_fingerprint() -> str:
    return fingerprint({str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in ("app/modules/rag", "app/modules/knowledge", "app/modules/assistants")
        for path in sorted(Path(directory).rglob("*.py"))})


def save_report(folder: Path, report: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False,
                                                indent=2, default=str), encoding="utf-8")


async def inspect_publication(assistant_code: str, filename: str) -> dict:
    """Re-resolve scope and publication after resets; enforce a read-only tx."""
    async with AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        assistant = await assistant_service.get_assistant(db, assistant_code)
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
            db, assistant.collection_id, tenant_id=assistant.tenant_id)
        sources = [dict(row) for row in (await db.execute(text("""
            SELECT b.id AS binding_id,b.status,i.id AS index_id,i.chunk_count,i.fact_count,
                   i.parity_report,s.id AS source_id,s.canonical_hash,s.canonical_markdown,
                   s.origin_file_hash,s.citation_metadata,s.snapshot_metadata,s.parse_provenance
            FROM knowledge_bindings b JOIN knowledge_index_revisions i
              ON i.id=b.active_index_revision_id
            JOIN knowledge_source_revisions s ON s.id=i.source_revision_v2_id
            WHERE b.collection_id=:collection AND b.tenant_id=:tenant
              AND b.workspace_id=:workspace AND b.status='active' AND i.status='active'
            ORDER BY b.id
        """), {"collection": snapshot.collection_id, "tenant": snapshot.tenant_id,
                "workspace": snapshot.workspace_id})).mappings()]
        targets = [row for row in sources if row["snapshot_metadata"].get("file_name") == filename]
        if len(targets) != 1:
            raise ValueError(f"Expected one published target, found {len(targets)}")
        target = targets[0]
        if snapshot.binding_revisions.get(target["binding_id"]) != target["index_id"]:
            raise ValueError("Target is outside the resolved publication")
        artifact = (target.pop("parse_provenance") or {}).get("structured_artifact", {})
        target["artifact"] = artifact
        facts = [dict(row) for row in (await db.execute(text("""
            SELECT id,entity_name,entity_code,attribute_name,attribute_value,attribute_code,
                   applicability_year,raw_data FROM knowledge_facts
            WHERE index_revision_id=:index ORDER BY entity_code,id
        """), {"index": target["index_id"]})).mappings()]
        chunks = [dict(row) for row in (await db.execute(text("""
            SELECT id,chunk_index,content,chunk_metadata,page_number FROM knowledge_chunks
            WHERE index_revision_id=:index ORDER BY chunk_index
        """), {"index": target["index_id"]})).mappings()]
        metadata = (await db.execute(text("SELECT collection_metadata FROM knowledge_collections WHERE id=:id"),
                                     {"id": snapshot.collection_id})).scalar_one()
        return {"assistant_code": assistant.code, "configuration_fingerprint": fingerprint(assistant.config),
            "configuration": serializable(assistant.config), "snapshot": snapshot.model_dump(),
            "snapshot_fingerprint": snapshot.cache_fingerprint(),
            "collection_metadata_fingerprint": fingerprint(metadata), "target": target,
            "facts": facts, "chunks": chunks,
            "target_data_fingerprint": fingerprint([target, facts, chunks]),
            "inventory": [{key: row[key] for key in ("binding_id", "index_id", "source_id", "canonical_hash")}
                          for row in sources]}


def inspect_pdf(path: Path, folder: Path) -> dict:
    """Render relevant physical pages, without invoking OCR or changing source."""
    with pymupdf.open(path) as document:
        pages = []
        for index, page in enumerate(document):
            item = {"page": index + 1, "native_text": page.get_text()}
            if index in (0, 1, 6, 7):
                image = folder / f"page_{index + 1}.png"
                page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6)).save(image)
                item["render"] = str(image.resolve())
            pages.append(item)
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "pages": pages}


def trace_async(target: Any, method: str, stages: list, *, kind: str = "normal") -> Any:
    original = getattr(target, method)

    async def observed(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        entry = {"stage": method, "arguments": serializable({k: v for k, v in kwargs.items() if k != "db"})}
        if kind == "model":
            request = next((arg for arg in args if hasattr(arg, "messages")), None)
            entry["request"] = serializable(request)
        stages.append(entry)
        try:
            result = await original(*args, **kwargs)
            entry["result"] = serializable(result)
            return result
        except Exception as exc:
            entry["error_type"] = type(exc).__name__
            entry["error_code"] = getattr(exc, "code", None)
            raise
        finally:
            entry["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)

    return observed


def trace_sync(target: Any, method: str, stages: list) -> Any:
    original = getattr(target, method)

    def observed(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        stages.append({"stage": method, "arguments": serializable(kwargs),
                       "result": serializable(result)})
        return result

    return observed


async def trace_case(case: dict, assistant_code: str, *, conversation_id: str | None = None) -> dict:
    from app.modules.rag import service as rag_module
    from app.modules.rag.service import rag_service

    stages: list[dict] = []
    conversation = conversation_id or "stage1_466_" + uuid.uuid4().hex[:16]
    result = {**case, "conversation_id": conversation, "stages": stages,
              "analysis": asdict(query_classifier.analyze(case["question"], module_code=assistant_code))}
    hooks = [(rag_module.fact_layer, "lookup_facts", "normal"),
             (rag_module.hybrid_retriever, "retrieve", "normal"),
             (rag_module.hybrid_retriever, "search_sparse_fts", "normal"),
             (vector_indexer, "search_dense", "normal"),
             (rag_module.hybrid_retriever, "expand_with_neighbors", "normal"),
             (rag_module.modelops_service, "generate", "model"), (rag_service, "ask", "normal")]
    started = time.perf_counter()
    with ExitStack() as stack:
        for target, method, kind in hooks:
            stack.enter_context(patch.object(target, method, trace_async(target, method, stages, kind=kind)))
        for method in ("verify_numeric_grounding", "filter_evidence_citations"):
            stack.enter_context(patch.object(rag_module.citation_guard, method,
                                            trace_sync(rag_module.citation_guard, method, stages)))
        async with AsyncSessionFactory() as db:
            try:
                response = await assistant_service.chat(db, assistant_code,
                    AssistantChatRequest(message=case["question"], conversation_id=conversation),
                    correlation_id=conversation)
                await db.commit()
                result["response"] = response.model_dump(mode="json")
            except Exception as exc:
                await db.rollback()
                result.update(error_type=type(exc).__name__, error_code=getattr(exc, "code", None))
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


async def run(args: argparse.Namespace) -> None:
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    report: dict = {"started_at": datetime.now(UTC).isoformat(), "results": [],
        "method": "Fresh read-only DB snapshot; optional in-process real assistant-service trace, not HTTP transport.",
        "runtime_files_modified": False,
        "code_fingerprint": runtime_fingerprint()}
    try:
        before = await inspect_publication(args.assistant, args.pdf.name)
        report["before"] = before
        report["pdf"] = inspect_pdf(args.pdf, folder)
        report["binary_matches_published_origin"] = report["pdf"]["sha256"] == before["target"]["origin_file_hash"]
        if not report["binary_matches_published_origin"]:
            raise ValueError("Local PDF differs from published source; refusing baseline")
        report["analyses"] = [{**case, "analysis": asdict(query_classifier.analyze(case["question"],
                              module_code=args.assistant))} for case in CASES]
        save_report(folder, report)
        if args.live:
            for case in CASES:
                current = await inspect_publication(args.assistant, args.pdf.name)
                if current["snapshot_fingerprint"] != before["snapshot_fingerprint"] or current["configuration_fingerprint"] != before["configuration_fingerprint"]:
                    raise ValueError("Publication/config changed before case; stopping")
                item = await trace_case(case, args.assistant)
                report["results"].append(item)
                save_report(folder, report)
                print(json.dumps({"case": case["id"], "status": item.get("response", {}).get("status"),
                                  "error": item.get("error_code"), "elapsed_ms": item["elapsed_ms"]}), flush=True)
        after = await inspect_publication(args.assistant, args.pdf.name)
        report["unchanged"] = {key: before[key] == after[key] for key in (
            "configuration_fingerprint", "snapshot_fingerprint", "target_data_fingerprint", "collection_metadata_fingerprint")}
        report["unchanged"]["runtime_code"] = report["code_fingerprint"] == runtime_fingerprint()
        report["finished_at"] = datetime.now(UTC).isoformat()
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error_code=getattr(exc, "code", None))
        raise
    finally:
        save_report(folder, report)
        await engine.dispose()
    print(json.dumps({"report": str(folder / "report.json"), "published_sources": len(before["inventory"]),
                      "binary_matches": report["binary_matches_published_origin"], "unchanged": report["unchanged"]}), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=Path("../docs/tai_lieu/tuyen_sinh/TB điểm sàn 26.pdf"))
    parser.add_argument("--output", type=Path, default=Path("storage/rag_stage1_466"))
    parser.add_argument("--assistant", default="admissions")
    parser.add_argument("--live", action="store_true", help="Create two ordinary test chats using genuine configured providers")
    asyncio.run(run(parser.parse_args()))
