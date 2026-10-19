"""Export verified source + annotation sidecars; external 'approved' is never authority."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from sqlalchemy import select

from app.core.storage import storage_service
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.services.qnu_serving import (
    load_document,
    standard_reference,
    verify_revision_pair,
)
from app.modules.knowledge.services.semantic_store import (
    effective_snapshot,
    identity,
    invalid,
    rebuild_projection,
    verify_effective_projection,
)

BUNDLE_SCHEMA = "qnu-semantic-bundle-v1"
MAX_BYTES = 32 * 1024 * 1024


async def export_revision_bundle(revision: Any) -> bytes:
    """Called only after server access checks. Does not mutate a source or publication."""
    document = await verify_revision_pair(revision)
    artifact = (revision.parse_provenance or {}).get("structured_artifact") or {}
    await verify_effective_projection(revision, artifact, document)
    reference = standard_reference(revision)
    files = {}
    pointers = {}
    for name, key, hash_key in [("source.qnu-rag-v1.md", "path", "sha256"),
                                 ("source.qnu-doc-v1.json", "structured_path", "structured_sha256")]:
        data = await storage_service.get(reference[key])
        if data is None or hashlib.sha256(data).hexdigest() != reference[hash_key]:
            raise invalid("export_source_checksum")
        files[name], pointers[reference[key]] = data, name
    raw = document.document_meta.get("raw_evidence")
    if raw:
        data = await storage_service.get(raw["path"])
        if data is None or hashlib.sha256(data).hexdigest() != raw["sha256"]:
            raise invalid("export_raw_evidence")
        files["source.raw-evidence"], pointers[raw["path"]] = data, "source.raw-evidence"
    active, _ = await effective_snapshot(revision)
    if active:
        data = await storage_service.get(active["path"])
        if data is None or hashlib.sha256(data).hexdigest() != active["sha256"]:
            raise invalid("export_semantic_checksum")
        files["source.qnu-semantic-v1.json"], pointers[active["path"]] = data, "source.qnu-semantic-v1.json"
    elif (artifact.get("semantic_annotations") or {}).get("status") == "verified":
        # A legacy approval can be recovered internally, but is not advertised
        # as an independently portable authoritative snapshot before backfill.
        raise invalid("legacy_snapshot_required", "SEMANTIC_LEGACY_REVIEW_REQUIRED")
    manifest = {"schema": BUNDLE_SCHEMA, "identity": identity(revision), "source_reference": reference,
                "snapshot_path": revision.snapshot_storage_path, "paths": pointers, "active": active,
                "semantics": "reviewed_sidecar" if active else "source_only",
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    files["manifest.json"] = (json.dumps(manifest, sort_keys=True, ensure_ascii=False) + "\n").encode()
    if sum(len(data) for data in files.values()) > MAX_BYTES:
        raise invalid("bundle_budget")
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), data)
    return stream.getvalue()


def _unpack(data: bytes) -> tuple[dict, dict[str, bytes]]:
    try:
        if len(data) > MAX_BYTES:
            raise invalid("bundle_budget")
        with ZipFile(BytesIO(data)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or len(names) > 8 or sum(i.file_size for i in archive.infolist()) > MAX_BYTES:
                raise invalid("bundle_members")
            if any("/" in name or "\\" in name or name in {".", ".."} for name in names):
                raise invalid("bundle_path")
            members = {name: archive.read(name) for name in names}
        manifest = json.loads(members.pop("manifest.json"))
        if manifest["schema"] != BUNDLE_SCHEMA or set(members) != set(manifest["files"]):
            raise invalid("bundle_manifest")
        if any(hashlib.sha256(value).hexdigest() != manifest["files"][name] for name, value in members.items()):
            raise invalid("bundle_checksum")
        if set(manifest["paths"].values()) != set(members) or len(manifest["paths"]) != len(members):
            raise invalid("bundle_paths")
        return manifest, members
    except (ValueError, KeyError, TypeError, OSError, BadZipFile) as exc:
        raise invalid("bundle_shape") from exc


async def read_external_bundle(data: bytes) -> dict:
    """Return untrusted candidates, even when an uploaded sidecar claims approved."""
    try:
        return await _read_external_bundle(data)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise invalid("external_bundle_shape") from exc


async def _read_external_bundle(data: bytes) -> dict:
    manifest, members = _unpack(data)
    # Use the existing pair verifier with an isolated byte reader; NEVER fetch a
    # path named by an external manifest from server Storage.
    class Reader:
        async def get(self, path: str) -> bytes | None:
            name = manifest["paths"].get(path)
            return members.get(name)

    reference = manifest["source_reference"]
    document = await load_document(reference, binding_id=manifest["identity"]["binding_id"],
        revision_id=manifest["identity"]["revision_id"], origin_hash=manifest["identity"]["origin_file_hash"],
        snapshot_path=manifest["snapshot_path"], storage=Reader())
    snapshot = json.loads(members["source.qnu-semantic-v1.json"]) if manifest["active"] else None
    if snapshot:
        active = manifest["active"]
        if (manifest["paths"].get(active.get("path")) != "source.qnu-semantic-v1.json"
                or manifest["files"].get("source.qnu-semantic-v1.json") != active.get("sha256")
                or snapshot.get("identity") != manifest["identity"]):
            raise invalid("external_sidecar_binding")
        from app.modules.knowledge.services.semantic_annotations import SemanticAnnotations

        annotations = SemanticAnnotations.model_validate(snapshot["proposal"]["annotations"]).model_dump()
    else:
        annotations = None
    return {"document": document, "manifest": manifest, "candidate": annotations, "trusted": False,
            "review_required": bool(snapshot)}


async def restore_internal_bundle(data: bytes, revision: Any) -> tuple[str, dict]:
    """A trusted caller supplies the authorized server revision, never a client 'trusted' flag."""
    loaded = await read_external_bundle(data)
    manifest = loaded["manifest"]
    reference, _ = await effective_snapshot(revision)
    if (manifest["identity"] != identity(revision) or manifest["source_reference"] != standard_reference(revision)
            or manifest["active"] != reference):
        raise invalid("bundle_authority", "SEMANTIC_SOURCE_MISMATCH")
    return await rebuild_projection(revision, loaded["document"])


async def download_revision_bundle(db: Any, collection_id: str, source_id: str, revision_id: str, actor: Any) -> bytes:
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
    from app.modules.knowledge.services.source_reparse import lock_source

    await lock_source(db, source_id)
    binding = await source_ingestion_service.get_source(db, collection_id, source_id, actor.tenant_id, actor.workspace_id)
    revision = (await db.execute(select(KnowledgeSourceRevision).where(
        KnowledgeSourceRevision.id == revision_id, KnowledgeSourceRevision.binding_id == binding.id
    ).execution_options(populate_existing=True))).scalar_one_or_none()
    if revision is None:
        raise invalid("revision_not_found", "SOURCE_REVISION_NOT_FOUND")
    return await export_revision_bundle(revision)
