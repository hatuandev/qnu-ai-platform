"""Explicit, workspace-owned dependency graph for permanent source or collection deletion."""

from sqlalchemy import and_, delete, or_, select, tuple_

from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform.database import Base
from qnu.platform.errors import Conflict, EntityNotFound

# Only this reviewed set can be purged; adding a new FK does not widen deletion silently.
SOURCE_TABLES = frozenset(
    {
        "kb_sources",
        "kb_source_revisions",
        "kb_preparation_intents",
        "ocr_processing_runs",
        "ocr_run_pages",
        "ocr_run_artifacts",
        "ocr_text_versions",
        "ocr_spelling_runs",
        "ocr_spelling_dispositions",
        "ocr_spelling_reviews",
        "kb_compilation_runs",
        "kb_compilation_inputs",
        "kb_compilation_artifacts",
        "kb_compilation_outputs",
        "kb_compilation_segments",
        "kb_compilation_segment_artifacts",
        "kb_compilation_reviews",
        "kb_compilation_review_artifacts",
        "kb_compilation_review_segments",
        "kb_compilation_review_segment_artifacts",
        "kb_compilation_review_jobs",
        "kb_compilation_edit_previews",
        "kb_compiled_versions",
        "kb_review_submissions",
        "kb_review_submission_previews",
        "kb_review_submission_actions",
        "kb_publication_previews",
        "kb_publication_decisions",
        "kb_index_inputs",
        "kb_index_chunks",
        "kb_compiled_documents",
        "chat_turns",
    }
)
# A collection purge owns whole index generations and folder rows, so runs and their
# manifest objects are deleted instead of resealed for surviving content.
COLLECTION_TABLES = SOURCE_TABLES | {
    "kb_collections",
    "kb_folders",
    "kb_index_runs",
    "kb_index_sync",
    "kb_upload_requests",
}
TABLES = COLLECTION_TABLES
MAX_ROWS = 10000
SEGMENT_OWNERS = {
    "kb_compilation_segments": "run_id",
    "kb_compilation_review_segments": "review_id",
}


def table(name):
    if name not in TABLES:
        raise Conflict(
            "Phụ thuộc ngoài phạm vi xóa đã hỗ trợ.", code="purge_dependency_unsupported"
        )
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


async def _close_dependencies(db, graph, workspace_id, scope):
    changed = True
    while changed:
        changed = False
        for name in sorted(scope - {"chat_turns"}):
            child = table(name)
            for fk in child.foreign_key_constraints:
                parent = fk.referred_table
                parents = graph.get(parent.name)
                if not parents:
                    continue
                keys = [
                    {c.name: row[c.name] for c in parent.primary_key.columns}
                    for row in parents.values()
                ]
                statement = (
                    select(child)
                    .join(
                        parent, and_(*(element.parent == element.column for element in fk.elements))
                    )
                    .where(selected(parent, keys))
                )
                # A self-reference needs distinct aliases to select child compiler generations.
                if child is parent:
                    alias = parent.alias("purge_parent")
                    statement = (
                        select(child)
                        .join(
                            alias,
                            and_(
                                *(
                                    element.parent == alias.c[element.column.name]
                                    for element in fk.elements
                                )
                            ),
                        )
                        .where(selected(alias, keys))
                    )
                changed |= await _add(db, graph, name, statement, workspace_id)


async def _guard_unsupported(db, graph, scope):
    for child in Base.metadata.tables.values():
        if child.name in scope:
            continue
        for fk in child.foreign_key_constraints:
            parent = fk.referred_table
            keys = list(graph.get(parent.name, {}).values())
            if keys and await db.scalar(
                select(1)
                .select_from(
                    child.join(
                        parent,
                        and_(*(element.parent == element.column for element in fk.elements)),
                    )
                )
                .where(selected(parent, keys))
                .limit(1)
            ):
                raise Conflict(
                    "Còn phụ thuộc chưa hỗ trợ xóa; chưa xóa dữ liệu.",
                    code="purge_dependency_unsupported",
                )


async def _add_empty_document_containers(db, graph, workspace_id):
    versions = list(graph.get("kb_compiled_versions", {}).values())
    docs, all_versions = table("kb_compiled_documents"), table("kb_compiled_versions")
    ids = [row["id"] for row in versions]
    doc_ids = {row["document_id"] for row in versions}
    await _add(
        db,
        graph,
        docs.name,
        select(docs).where(
            docs.c.id.in_(doc_ids),
            ~docs.c.id.in_(
                select(all_versions.c.document_id).where(
                    all_versions.c.id.not_in(ids),
                )
            ),
        ),
        workspace_id,
    )


async def _add_citing_turns(db, graph, workspace_id):
    versions = list(graph.get("kb_compiled_versions", {}).values())
    ids = [row["id"] for row in versions]
    if not ids:
        return
    turns = table("chat_turns")
    await _add(
        db,
        graph,
        turns.name,
        select(turns).where(
            turns.c.workspace_id == workspace_id,
            or_(*(turns.c.result["sources"].contains([{"version_id": value}]) for value in ids)),
        ),
        workspace_id,
    )


def _check_approved_plan(graph, allow_published):
    versions = list(graph.get("kb_compiled_versions", {}).values())
    if any(row["status"] == "published" for row in versions) and not allow_published:
        raise Conflict(
            "Tài liệu đang được phát hành. Hãy thu hồi/dừng phát hành các bản liên quan trước khi xóa.",
            code="source_publication_in_use",
        )
    for name, owner_field in SEGMENT_OWNERS.items():
        segments = graph.get(name, {})
        for row in segments.values():
            if row["parent_segment_id"] is None:
                continue
            parent = segments.get((row["parent_segment_id"],))
            if parent is None or parent[owner_field] != row[owner_field]:
                raise Conflict("Nhóm xử lý ngoài phạm vi xóa.", code="purge_scope_invalid")


async def graph_for_source(db, workspace_id, source_id, *, allow_published: bool = False):
    source, ocr, inputs, runs = map(
        table,
        (
            "kb_sources",
            "ocr_processing_runs",
            "kb_compilation_inputs",
            "kb_compilation_runs",
        ),
    )
    graph = {}
    await _add(
        db,
        graph,
        source.name,
        select(source).where(
            source.c.id == source_id,
            source.c.workspace_id == workspace_id,
        ),
        workspace_id,
    )
    if not graph[source.name]:
        raise EntityNotFound("Không tìm thấy tài liệu.", code="source_not_found")
    compiler_ids = (
        select(inputs.c.run_id)
        .join(ocr, inputs.c.ocr_run_id == ocr.c.id)
        .where(
            ocr.c.source_id == source_id,
            ocr.c.workspace_id == workspace_id,
        )
    )
    versions_table = table("kb_compiled_versions")
    provenance_runs = select(versions_table.c.compilation_run_id).where(
        versions_table.c.workspace_id == workspace_id,
        versions_table.c.provenance["sources"].contains([{"identity": {"source_id": source_id}}]),
    )
    await _add(
        db,
        graph,
        runs.name,
        select(runs).where(
            or_(
                runs.c.id.in_(compiler_ids),
                runs.c.id.in_(provenance_runs),
            )
        ),
        workspace_id,
    )
    await _close_dependencies(db, graph, workspace_id, SOURCE_TABLES)
    _check_approved_plan(graph, allow_published)
    # Remove empty document containers only; documents with other versions remain intact.
    await _add_empty_document_containers(db, graph, workspace_id)
    # Historical turns containing these citations also contain copied document text.
    await _add_citing_turns(db, graph, workspace_id)
    await _guard_unsupported(db, graph, SOURCE_TABLES)
    return graph


async def graph_for_collection(db, workspace_id, collection_id, *, allow_published: bool = False):
    collections, uploads = table("kb_collections"), table("kb_upload_requests")
    graph = {}
    await _add(
        db,
        graph,
        collections.name,
        select(collections).where(
            collections.c.id == collection_id,
            collections.c.workspace_id == workspace_id,
        ),
        workspace_id,
    )
    if not graph[collections.name]:
        raise EntityNotFound("Không tìm thấy kho tri thức.", code="collection_not_found")
    assistants = Base.metadata.tables["chat_assistants"]
    if await db.scalar(
        select(assistants.c.id)
        .where(
            assistants.c.workspace_id == workspace_id,
            assistants.c.collection_id == collection_id,
        )
        .limit(1)
    ):
        raise Conflict(
            "Kho đang được trợ lý sử dụng. Hãy gỡ kho khỏi trợ lý trước khi xóa.",
            code="collection_in_use_by_assistants",
        )
    # The upload ledger has no FK to the collection but would replay deleted ids.
    await _add(
        db,
        graph,
        uploads.name,
        select(uploads).where(
            uploads.c.collection_id == collection_id,
            uploads.c.workspace_id == workspace_id,
        ),
        workspace_id,
    )
    await _close_dependencies(db, graph, workspace_id, COLLECTION_TABLES)
    _check_approved_plan(graph, allow_published)
    await _add_empty_document_containers(db, graph, workspace_id)
    await _add_citing_turns(db, graph, workspace_id)
    await _guard_unsupported(db, graph, COLLECTION_TABLES)
    return graph


def graph_plan(graph):
    rows, objects = {}, {}

    def add_object(key, sha):
        if not key:
            return
        previous = objects.get(key)
        if previous and sha and previous != sha:
            raise Conflict("Các tham chiếu object mâu thuẫn hash.", code="purge_object_changed")
        objects[key] = sha or previous

    for name, values in sorted(graph.items()):
        target = table(name)
        ordered = sorted(
            values.values(),
            key=lambda row: tuple(str(row[c.name]) for c in target.primary_key.columns),
        )
        rows[name] = [{c.name: row[c.name] for c in target.primary_key.columns} for row in ordered]
        for row in ordered:
            if name == "kb_source_revisions":
                add_object(row["storage_key"], row["sha256"])
            if name == "ocr_run_pages":
                add_object(row["image_key"], row["image_sha256"])
                add_object(row["raw_key"], row["raw_sha256"])
            if name in {
                "ocr_run_artifacts",
                "kb_compilation_artifacts",
                "kb_compilation_segment_artifacts",
                "kb_compilation_review_artifacts",
                "kb_compilation_review_segment_artifacts",
            }:
                add_object(row["blob_key"], row["sha256"])
            if name == "kb_compilation_outputs":
                add_object(row["draft_blob_key"], row["draft_sha256"])
                add_object(row["markdown_blob_key"], row["markdown_sha256"])
            if name == "ocr_text_versions":
                add_object(row["document_key"], row["canonical_sha256"])
                add_object(row["markdown_key"], row["markdown_sha256"])
            if name == "ocr_spelling_runs":
                add_object(f"ocr-spelling/{row['workspace_id']}/{row['id']}/raw-response", None)
            if name == "kb_index_runs":
                add_object(row["manifest_key"], row["manifest_sha256"])
                for receipt in row.get("batch_receipts") or []:
                    add_object(receipt.get("raw_key"), receipt.get("raw_sha256"))
    # Cancelled workers may still settle usage/timestamps. Fence the approved deletion
    # scope and immutable payload identities, rather than those bookkeeping fields.
    return {
        "rows": rows,
        "objects": objects,
        "graph_sha256": digest({"rows": rows, "objects": objects}),
    }


async def delete_rows(db, plan, workspace_id):
    for target in reversed(Base.metadata.sorted_tables):
        keys = plan["rows"].get(target.name, [])
        if not keys:
            continue
        parent_field = {
            "kb_compilation_runs": "parent_run_id",
            "kb_compilation_segments": "parent_segment_id",
            "kb_compilation_review_segments": "parent_segment_id",
        }.get(target.name)
        if parent_field:
            # Delete edit and refinement leaves before their self-referenced parents.
            while await db.scalar(select(target.c.id).where(selected(target, keys)).limit(1)):
                child = target.alias("purge_child")
                result = await db.execute(
                    delete(target).where(
                        selected(target, keys),
                        ~select(child.c.id)
                        .where(
                            child.c[parent_field] == target.c.id,
                        )
                        .exists(),
                    )
                )
                if not result.rowcount:
                    raise Conflict(
                        "Chuỗi biên soạn còn phụ thuộc.", code="purge_dependency_changed"
                    )
        else:
            await db.execute(delete(target).where(selected(target, keys)))
    states = Base.metadata.tables["resource_lifecycle_states"]
    for name, kind in (
        ("kb_collections", "collection"),
        ("kb_folders", "folder"),
        ("kb_sources", "source"),
        ("kb_compiled_documents", "document"),
    ):
        ids = [key["id"] for key in plan["rows"].get(name, [])]
        if ids:
            await db.execute(
                delete(states).where(
                    states.c.workspace_id == workspace_id,
                    states.c.kind == kind,
                    states.c.resource_id.in_(ids),
                )
            )
