"""Bounded structural refinement, with durable parent/child source ownership."""

import hashlib
import json
from typing import NoReturn

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation import segments as split
from qnu.domains.knowledge.compilation.artifacts import json_bytes, store_segment
from qnu.domains.knowledge.compilation.drafting import markdown_for
from qnu.domains.knowledge.compilation.evidence import literal_tables
from qnu.domains.knowledge.compilation.lease import assert_claim, commit_owned
from qnu.domains.knowledge.compilation.models import CompilationRun, CompilationSegment, utcnow
from qnu.domains.knowledge.compilation.projection import project_documents
from qnu.domains.ocr.ids import new_id
from qnu.platform.errors import AppException
from qnu.ports.blob_store import BlobStore


def reject(code: str) -> NoReturn:
    raise AppException("Không thể chia tiếp phần biên soạn an toàn.", code=code, status_code=422)


def diagnose(raw: bytes) -> bool:
    """Only a definite length stop with visible output is eligible; no 422 heuristic."""
    try:
        choice = json.loads(raw)["choices"][0]
        return choice.get("finish_reason") == "length" and bool(
            (choice["message"].get("content") or "").strip()
        )
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return False


def request_usage(node: CompilationSegment) -> int | None:
    return node.config.get("refined_usage_tokens", node.usage_tokens)


def total_usage(nodes: list[CompilationSegment]) -> int | None:
    values = [request_usage(node) for node in nodes if node.request_started_at is not None]
    return None if not values or any(value is None for value in values) else sum(values)


def partition(documents: list[dict], scope: dict) -> list[list[split.Unit]]:
    refs = scope["owned"]
    atoms = {
        (r["ocr_run_id"], r["page"], r["evidence_id"], row)
        for r in refs
        for row in r.get("rows", [None])
    }
    units = [
        u
        for u in split.build_units(documents)
        if (u.ocr_run_id, u.page_number, u.evidence_id, u.row_index) in atoms
    ]
    if len(units) != len(atoms):
        reject("compilation_refinement_scope_invalid")
    # Never cut a rowspan across children. Headers are shared context.
    candidates = []
    for cut in range(1, len(units)):
        left, right = units[cut - 1], units[cut]
        safe = True
        if (
            left.evidence_id == right.evidence_id
            and left.ocr_run_id == right.ocr_run_id
            and right.row_index is not None
        ):
            block = documents[right.document_index]["pages"][right.page_index]["blocks"][
                right.block_index
            ]
            for row_index, row in enumerate(block["table"]["rows"][: right.row_index]):
                if row_index in right.header_rows:
                    continue
                if any(row_index + (cell.get("row_span") or 1) > right.row_index for cell in row):
                    safe = False
        if safe:
            candidates.append(cut)
    if not candidates:
        reject("compilation_refinement_atomic_limit")
    middle = min(candidates, key=lambda cut: abs(cut - len(units) / 2))
    return [units[:middle], units[middle:]]


async def children(
    db: AsyncSession, run: CompilationRun, segment: CompilationSegment
) -> list[CompilationSegment]:
    return list(
        (
            await db.scalars(
                select(CompilationSegment)
                .where(
                    CompilationSegment.run_id == run.id,
                    CompilationSegment.parent_segment_id == segment.id,
                )
                .order_by(CompilationSegment.segment_index)
            )
        ).all()
    )


async def create_children(
    db: AsyncSession,
    run: CompilationRun,
    segment: CompilationSegment,
    documents: list[dict],
    raw: bytes,
) -> list[CompilationSegment]:
    policy = run.config.get("refinement")
    if not policy or not diagnose(raw):
        return []
    depth = segment.config.get("depth", 0)
    if depth >= policy["max_depth"]:
        reject("compilation_refinement_depth_exhausted")
    groups = partition(documents, segment.scope)
    await assert_claim(db, run)  # Serializes index allocation across root workers.
    count = await db.scalar(
        select(func.count())
        .select_from(CompilationSegment)
        .where(
            CompilationSegment.run_id == run.id,
        )
    )
    if count + 2 > policy["max_nodes"]:
        reject("compilation_refinement_nodes_exhausted")
    index = (
        await db.scalar(
            select(func.max(CompilationSegment.segment_index)).where(
                CompilationSegment.run_id == run.id,
            )
        )
    ) + 1
    total = index + 1
    parent_plan = split.plan_from_scope(segment.scope)
    parts = []
    for offset, group in enumerate(groups):
        plan = split.build_plan(
            index=index + offset,
            units=group,
            documents=documents,
            topic=run.topic,
            structured=bool(segment.config.get("structured_output")),
            total_estimate=total,
            projection=parent_plan.projection,
        )
        # Preserve parent qualifications, including cross-part context selected earlier.
        context = tuple(
            {
                json.dumps(ref, sort_keys=True): ref
                for ref in (
                    *parent_plan.context,
                    *plan.context,
                )
            }.values()
        )
        payload, citations = split.build_projection(
            run.topic,
            documents,
            plan.owned,
            context,
            plan.index,
            total=total,
            projection=plan.projection,
        )
        scope = {**plan.scope_dict(), "context": list(context)}
        input_hash = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        schema = (
            split.segment_schema(citations) if segment.config.get("structured_output") else None
        )
        schema_hash = hashlib.sha256(json_bytes(schema)).hexdigest() if schema else None
        scope.update(input_sha256=input_hash, schema_sha256=schema_hash)
        child = CompilationSegment(
            id=new_id("cseg"),
            run_id=run.id,
            parent_segment_id=segment.id,
            segment_index=plan.index,
            status="pending",
            scope=scope,
            input_sha256=input_hash,
            schema_sha256=schema_hash,
            prompt_version=split.prompt_version_for(plan.projection),
            config={
                **segment.config,
                "depth": depth + 1,
                "request_total": total,
                "path": f"{segment.config.get('path', segment.segment_index)}.{offset + 1}",
            },
            request_hash=hashlib.sha256(
                json_bytes({"parent": segment.request_hash, "scope": scope})
            ).hexdigest(),
            attempt_count=0,
        )
        db.add(child)
        parts.append(child)
    segment.config = {**segment.config, "refined_usage_tokens": segment.usage_tokens}
    segment.status, segment.error_code, segment.finished_at = "running", None, None
    await commit_owned(db, run)
    return parts


def node_content(
    segment: CompilationSegment, draft: dict, documents: list[dict], children_ids=()
) -> dict:
    projected = project_documents(documents, segment.scope["owned"], [])
    return {
        **draft,
        "source_tables": literal_tables(projected),
        "node": {
            "id": segment.id,
            "parent_id": segment.parent_segment_id,
            "index": segment.segment_index,
            "path": str(segment.config.get("path", segment.segment_index)),
            "run_id": segment.run_id,
            "source_scope": segment.scope["owned"],
            "children": list(children_ids),
        },
    }


async def save_pair(
    db: AsyncSession, blob: BlobStore, run: CompilationRun, segment: CompilationSegment, draft: dict
) -> None:
    await assert_claim(db, run)
    child_nodes = await children(db, run, segment)
    parent = (
        await db.get(CompilationSegment, segment.parent_segment_id)
        if segment.parent_segment_id
        else None
    )
    if parent is not None and parent.run_id != run.id:
        reject("compilation_refinement_scope_invalid")

    def references(index: int) -> dict:
        return {
            "json": f"../../{index}/artifacts/draft_json",
            "markdown": f"../../{index}/artifacts/markdown",
        }

    draft["node"]["artifacts"] = {
        **references(segment.segment_index),
        "document": {"json": "../../../draft", "markdown": "../../../markdown"},
        "parent": references(parent.segment_index) if parent else None,
        "children": [{"id": node.id, **references(node.segment_index)} for node in child_nodes],
    }
    await store_segment(db, blob, run, segment, "draft_json", json_bytes(draft))
    links = "\n".join(
        f"- [Phần {child.segment_index}](../../{child.segment_index}/artifacts/markdown)"
        for child in child_nodes
    )
    await store_segment(
        db,
        blob,
        run,
        segment,
        "markdown",
        (
            markdown_for(draft)
            + "\n[Toàn tài liệu](../../../markdown)\n"
            + (f"\n[Phần cha]({references(parent.segment_index)['markdown']})\n" if parent else "")
            + ("\n## Phần con\n\n" + links + "\n" if links else "")
        ).encode(),
    )
    segment.status, segment.error_code, segment.finished_at = "completed", None, utcnow()
    await commit_owned(db, run)
