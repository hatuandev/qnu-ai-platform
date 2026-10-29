"""Explicit, workspace-owned dependency graph for permanent source deletion."""

import json

from sqlalchemy import and_, cast, delete, or_, select, String, tuple_

from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform.database import Base
from qnu.platform.errors import Conflict

# Only this reviewed set can be purged; adding a new FK does not widen deletion silently.
TABLES = frozenset({
    "kb_sources", "kb_source_revisions", "ocr_processing_runs", "ocr_run_pages",
    "ocr_run_artifacts", "ocr_text_versions", "ocr_spelling_runs", "kb_compilation_runs",
    "kb_compilation_inputs", "kb_compilation_artifacts", "kb_compilation_reviews",
    "kb_compilation_review_artifacts", "kb_compilation_review_jobs", "kb_compilation_edit_previews",
    "kb_compiled_versions", "kb_publication_previews", "kb_publication_decisions",
    "kb_index_inputs", "kb_index_chunks", "kb_compiled_documents", "chat_turns",
})
MAX_ROWS = 50000


def table(name):
    if name not in TABLES:
        raise Conflict("Phụ thuộc ngoài phạm vi xóa đã hỗ trợ.", code="purge_dependency_unsupported")
    return Base.metadata.tables[name]


def selected(target, keys):
    columns = list(target.primary_key)
    return tuple_(*columns).in_([tuple(row[c.name] for c in columns) for row in keys])


async def _add(db, graph, name, statement, workspace_id):
    target = table(name)
    values = list((await db.execute(statement.limit(MAX_ROWS + 1))).mappings())
    if len(values) > MAX_ROWS or any(
        row.get("workspace_id", workspace_id) != workspace_id for row in values
    ):
        raise Conflict("Phạm vi xóa không hợp lệ hoặc quá lớn.", code="purge_scope_invalid")
    found = graph.setdefault(name, {})
    before = len(found)
    for row in values:
        found[tuple(row[c.name] for c in target.primary_key.columns)] = dict(row)
    if sum(map(len, graph.values())) > MAX_ROWS:
        raise Conflict("Quá nhiều dữ liệu phụ thuộc để xóa một lượt.", code="purge_limit")
    return len(found) != before


async def graph_for_source(db, workspace_id, source_id):
    source, ocr, inputs, runs = map(table, (
        "kb_sources", "ocr_processing_runs", "kb_compilation_inputs", "kb_compilation_runs",
    ))
    graph = {}
    await _add(db, graph, source.name, select(source).where(
        source.c.id == source_id, source.c.workspace_id == workspace_id,
    ), workspace_id)
    compiler_ids = select(inputs.c.run_id).join(ocr, inputs.c.ocr_run_id == ocr.c.id).where(
        ocr.c.source_id == source_id, ocr.c.workspace_id == workspace_id,
    )
    await _add(db, graph, runs.name, select(runs).where(runs.c.id.in_(compiler_ids)), workspace_id)
    changed = True
    while changed:
        changed = False
        for name in sorted(TABLES - {"chat_turns"}):
            child = table(name)
            for fk in child.foreign_key_constraints:
                parent = fk.referred_table
                parents = graph.get(parent.name)
                if not parents:
                    continue
                keys = [{c.name: row[c.name] for c in parent.primary_key.columns} for row in parents.values()]
                statement = select(child).join(parent, and_(*(
                    element.parent == element.column for element in fk.elements
                ))).where(selected(parent, keys))
                # A self-reference needs distinct aliases to select child compiler generations.
                if child is parent:
                    alias = parent.alias("purge_parent")
                    statement = select(child).join(alias, and_(*(
                        element.parent == alias.c[element.column.name] for element in fk.elements
                    ))).where(selected(alias, keys))
                changed |= await _add(db, graph, name, statement, workspace_id)
    versions = list(graph.get("kb_compiled_versions", {}).values())
    if any(row["status"] == "published" for row in versions):
        raise Conflict(
            "Tài liệu đang được phát hành. Hãy thu hồi/dừng phát hành các bản liên quan trước khi xóa.",
            code="source_publication_in_use",
        )
    # Remove empty document containers only; documents with other versions remain intact.
    docs, all_versions = table("kb_compiled_documents"), table("kb_compiled_versions")
    ids = [row["id"] for row in versions]
    doc_ids = {row["document_id"] for row in versions}
    await _add(db, graph, docs.name, select(docs).where(
        docs.c.id.in_(doc_ids), ~docs.c.id.in_(select(all_versions.c.document_id).where(
            all_versions.c.id.not_in(ids),
        )),
    ), workspace_id)
    # Historical turns containing these citations also contain copied document text.
    turns = table("chat_turns")
    identifiers = [source_id, *ids]
    await _add(db, graph, turns.name, select(turns).where(
        turns.c.workspace_id == workspace_id,
        or_(*(cast(turns.c.result, String).contains(value) for value in identifiers)),
    ), workspace_id)
    return graph


def graph_plan(graph):
    rows, checks, objects = {}, {}, {}
    for name, values in sorted(graph.items()):
        target = table(name)
        ordered = sorted(values.values(), key=lambda row: tuple(str(row[c.name]) for c in target.primary_key.columns))
        rows[name] = [{c.name: row[c.name] for c in target.primary_key.columns} for row in ordered]
        checks[name] = digest(json.loads(json.dumps(ordered, default=str)))
        for row in ordered:
            if name == "kb_source_revisions":
                objects[row["storage_key"]] = row["sha256"]
            if name in {"ocr_run_artifacts", "kb_compilation_artifacts", "kb_compilation_review_artifacts"}:
                objects[row["blob_key"]] = row["sha256"]
            if name == "ocr_text_versions":
                objects[row["document_key"]] = row["canonical_sha256"]
                objects[row["markdown_key"]] = row["markdown_sha256"]
            if name == "ocr_spelling_runs":
                objects[f"ocr-spelling/{row['workspace_id']}/{row['id']}/raw-response"] = None
    return {"rows": rows, "objects": objects, "graph_sha256": digest(checks)}


async def delete_rows(db, plan, workspace_id):
    for target in reversed(Base.metadata.sorted_tables):
        keys = plan["rows"].get(target.name, [])
        if not keys:
            continue
        if target.name == "kb_compilation_runs":
            # Immutable edit ancestry is a self-FK; delete leaves before their parents.
            while await db.scalar(select(target.c.id).where(selected(target, keys)).limit(1)):
                child = target.alias("purge_child")
                result = await db.execute(delete(target).where(
                    selected(target, keys), ~select(child.c.id).where(
                        child.c.parent_run_id == target.c.id,
                    ).exists(),
                ))
                if not result.rowcount:
                    raise Conflict("Chuỗi biên soạn còn phụ thuộc.", code="purge_dependency_changed")
        else:
            await db.execute(delete(target).where(selected(target, keys)))
    states = Base.metadata.tables["resource_lifecycle_states"]
    ids = [key["id"] for name in ("kb_sources", "kb_compiled_documents") for key in plan["rows"].get(name, [])]
    await db.execute(delete(states).where(
        states.c.workspace_id == workspace_id, states.c.kind.in_(("source", "document")),
        states.c.resource_id.in_(ids),
    ))
