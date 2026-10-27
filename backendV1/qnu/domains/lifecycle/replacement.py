"""Build a candidate generation against an approved draft; publish and activate atomically."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.models import IndexInput, IndexRun
from qnu.domains.knowledge.index.schemas import IndexRequest
from qnu.domains.knowledge.index.snapshots import current_snapshot, publication_identity
from qnu.domains.knowledge.models import KBSource
from qnu.domains.knowledge.publication.access import authorize, document, version
from qnu.domains.knowledge.publication.decisions import (
    _apply,
    assert_approval_receipt,
    preview_material,
)
from qnu.domains.knowledge.publication.evidence import assert_pinned, digest, load_bundle
from qnu.domains.knowledge.publication.models import (
    CompiledDocument,
    CompiledVersion,
    PublicationDecision,
    PublicationPreview,
)
from qnu.domains.knowledge.publication.reading import read_published
from qnu.domains.knowledge.publication.schemas import (
    DecisionResponse,
    DocumentResponse,
    PublishedResponse,
    VersionResponse,
)
from qnu.domains.lifecycle.models import LifecycleAction
from qnu.domains.ocr.ids import new_id
from qnu.domains.operations.service import background_actor
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue
from qnu.ports.vector_store import VectorStore


async def candidate(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, doc: CompiledDocument, parameters: dict
) -> tuple[list[PublishedResponse], dict, CompiledVersion, list[dict]]:
    await authorize(db, actor, doc.workspace_id, doc.collection_id, action="publish")
    # Persisted work rechecks membership, so require a real unit-admin grant before queuing.
    await authorize(
        db, background_actor(actor), doc.workspace_id, doc.collection_id, action="publish"
    )
    doc = await document(db, doc.workspace_id, doc.collection_id, doc.id, lock=True)
    version_id = parameters.get("replacement_version_id")
    if not version_id:
        raise Conflict("Cần phiên bản mới đã được duyệt.", code="replacement_version_required")
    target = await version(db, doc, version_id)
    if target.status != "approved":
        raise Conflict("Phiên bản thay thế chưa được duyệt.", code="publication_approval_required")
    await assert_approval_receipt(db, target, blob)
    bundle = await load_bundle(
        db,
        blob,
        doc.workspace_id,
        doc.collection_id,
        target.compilation_run_id,
        require_current=True,
        allow_staged=True,
    )
    assert_pinned(target, bundle)
    receipt = await db.scalar(
        select(PublicationDecision)
        .where(PublicationDecision.version_id == target.id, PublicationDecision.action == "approve")
        .order_by(PublicationDecision.document_sequence.desc())
        .limit(1)
    )
    approved = PublishedResponse(
        document=DocumentResponse.model_validate(doc),
        version=VersionResponse.model_validate(target),
        decision=DecisionResponse.model_validate(receipt),
        content=bundle.content,
    )
    current = await current_snapshot(db, blob, actor, doc.workspace_id, doc.collection_id)
    if doc.id not in {p.document.id for p in current}:
        raise Conflict(
            "Thay thế yêu cầu tài liệu đang xuất bản.", code="replacement_active_required"
        )
    identities = [source["identity"] for source in bundle.provenance["sources"]]
    switching = {}
    source_states = []
    for identity in identities:
        source = await db.get(KBSource, identity["source_id"], populate_existing=True)
        source_states.append(
            {
                "id": source.id,
                "latest": source.latest_revision_no,
                "serving": source.serving_revision_no,
                "candidate": identity["revision_no"],
            }
        )
        if source.serving_revision_no != identity["revision_no"]:
            switching[source.id] = identity["revision_no"]
    for published in current:
        if published.document.id == doc.id:
            continue
        for source in published.version.provenance["sources"]:
            identity = source["identity"]
            if (
                identity["source_id"] in switching
                and identity["revision_no"] != switching[identity["source_id"]]
            ):
                raise Conflict(
                    "Nguồn dùng chung còn được văn bản khác xuất bản; cần thu hồi hoặc thay thế đồng bộ trước.",
                    code="replacement_shared_source",
                )
    publications = sorted(
        [approved if p.document.id == doc.id else p for p in current], key=lambda p: p.document.id
    )
    plan = {
        "document_sequence": doc.change_sequence,
        "current": [publication_identity(p) for p in current],
        "candidate": publication_identity(approved),
        "sources": source_states,
    }
    return publications, plan, target, identities


async def inspect_replacement(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, doc: CompiledDocument, parameters: dict
) -> tuple[dict, dict]:
    publications, plan, _, _ = await candidate(db, blob, actor, doc, parameters)
    return plan, {
        "version_id": parameters["replacement_version_id"],
        "documents_in_new_index": len(publications),
        "keeps_current_until_ready": True,
    }


async def prepare_replacement(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    queue: JobQueue | None,
    actor: AuthActor,
    action: LifecycleAction,
    doc: CompiledDocument,
) -> LifecycleAction:
    from qnu.domains.knowledge.index.service import dispatch, request_index

    publications, plan, _, _ = await candidate(db, blob, actor, doc, action.parameters)
    # A queue cannot see this run until its action, chunks and approval intent commit together.
    outcome = await request_index(
        db,
        blob,
        vectors,
        actor,
        action.workspace_id,
        doc.collection_id,
        IndexRequest(),
        "replacement:" + action.id,
        None,
        prepared_publications=publications,
        replacement_action_id=action.id,
        replacement_plan_sha256=digest(plan),
        commit=False,
    )
    action.result = {"index_run_id": outcome.run.id, "current_publication_retained": True}
    await db.commit()
    await dispatch(db, outcome.run, queue)
    return action


async def prepared_snapshot(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, run: IndexRun
) -> list[PublishedResponse]:
    action = await db.get(
        LifecycleAction, run.config["replacement_action_id"], populate_existing=True
    )
    if (
        action is None
        or action.workspace_id != run.workspace_id
        or action.status != "pending"
        or action.actor_ref != run.requested_by
    ):
        raise Conflict("Thao tác thay thế không còn hiệu lực.", code="replacement_action_stale")
    doc = await document(db, run.workspace_id, run.collection_id, action.resource_id, lock=True)
    publications, plan, _, _ = await candidate(db, blob, actor, doc, action.parameters)
    if digest(plan) != run.config["replacement_plan_sha256"]:
        raise Conflict(
            "Nguồn hoặc quyết định duyệt đã đổi trong khi chuẩn bị.",
            code="replacement_snapshot_changed",
        )
    return publications


async def activate_replacement(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, run: IndexRun
) -> list[PublishedResponse]:
    """Caller retains the workspace lock and commits publication, source pointer and index once."""
    await prepared_snapshot(db, blob, actor, run)
    with db.no_autoflush:
        action = await db.get(LifecycleAction, run.config["replacement_action_id"])
    doc = await document(db, run.workspace_id, run.collection_id, action.resource_id, lock=True)
    _, _, target, identities = await candidate(db, blob, actor, doc, action.parameters)
    active = await read_published(db, blob, actor, run.workspace_id, run.collection_id, doc.id)
    preview = PublicationPreview(
        id=new_id("pprev"),
        workspace_id=run.workspace_id,
        collection_id=run.collection_id,
        document_id=doc.id,
        version_id=target.id,
        actor_ref=actor_ref(actor),
        action="publish",
        reason=action.reason[:1000],
        expected_document_sequence=doc.change_sequence,
        expected_version_sequence=target.state_version,
        expected_active_version_id=active.version.id,
        bundle_sha256=target.bundle_sha256,
        expires_at=utcnow() + timedelta(seconds=get_settings().PUBLICATION_PREVIEW_TTL_SECONDS),
    )
    preview.preview_sha256 = digest(preview_material(preview))
    db.add(preview)
    await db.flush()
    for identity in identities:
        source = await db.get(KBSource, identity["source_id"])
        source.serving_revision_no = identity["revision_no"]
    decision = await _apply(
        db,
        actor,
        doc,
        target,
        preview,
        "replacement:" + action.id,
        digest({"lifecycle_action": action.id, "index_run": run.id}),
        commit=False,
    )
    binding = await db.scalar(
        select(IndexInput).where(IndexInput.run_id == run.id, IndexInput.document_id == doc.id)
    )
    binding.publication_decision_id, binding.version_state = decision.id, target.state_version
    await db.flush()
    publications = await current_snapshot(db, blob, actor, run.workspace_id, run.collection_id)
    run.input_sha256 = digest([publication_identity(p) for p in publications])
    action.status, action.finished_at = "completed", utcnow()
    action.result = {
        **action.result,
        "publication_decision_id": decision.id,
        "current_publication_retained": False,
    }
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="lifecycle.completed",
        detail={"action_id": action.id, "index_run_id": run.id, "operation": "replace"},
    )
    return publications


async def fail_replacement(db: AsyncSession, run: IndexRun, code: str) -> None:
    if not run.config.get("replacement_action_id"):
        return
    with db.no_autoflush:
        action = await db.get(LifecycleAction, run.config["replacement_action_id"])
    if action and action.status == "pending":
        action.status, action.error_code, action.finished_at = "failed", code, utcnow()
