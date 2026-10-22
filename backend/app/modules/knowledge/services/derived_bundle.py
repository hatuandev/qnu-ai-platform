"""Integrity seals, not semantic approval, for revision-bound RAG derivatives."""

import hashlib
import json
from typing import Any

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_units import (
    manifest_digest,
    resolve_unit_manifest,
)
from app.modules.knowledge.normalization.structure_chunks import CHUNK_VERSION

BUNDLE_VERSION = "derived-bundle-v1"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def source_fingerprint(source: Any, artifact: dict) -> dict:
    actual_hash = hashlib.sha256((source.canonical_markdown or "").encode()).hexdigest()
    try:
        units = resolve_unit_manifest(source.canonical_markdown or "", artifact)
        graph = artifact.get("context_graph")
        if graph:
            from app.modules.knowledge.services.source_links import validate_context_graph

            validate_context_graph(graph, units)
        if (source.canonical_hash != actual_hash or artifact.get("content_hash") != actual_hash
                or artifact.get("fact_set_hash") != digest(artifact.get("facts", []))):
            raise ValueError("Derivative hash mismatch")
    except (TypeError, ValueError, KeyError) as error:
        raise AppException("Bản sạch và dữ liệu dẫn xuất không còn khớp.", code="DERIVED_BUNDLE_INVALID", status_code=409) from error
    fingerprint = {
        "source_revision_id": source.id, "binding_id": source.binding_id,
        "origin_document_id": source.origin_document_id, "snapshot_metadata_hash": digest(source.snapshot_metadata),
        "origin_file_hash": source.origin_file_hash, "canonical_hash": actual_hash,
        "normalizer_version": source.normalizer_version, "parser_profile_hash": source.parser_profile_hash,
        "page_manifest_hash": digest(source.page_manifest), "citation_metadata_hash": digest(source.citation_metadata),
        "unit_manifest_hash": manifest_digest(units), "context_graph_hash": graph["digest"] if graph else None,
        "fact_set_hash": artifact["fact_set_hash"],
    }
    if artifact.get("semantic_effective"):
        fingerprint["semantic_annotation_hash"] = artifact["semantic_effective"]["semantic_hash"]
        fingerprint["semantic_snapshot_sha256"] = artifact["semantic_effective"]["snapshot_sha256"]
    wiki_policy = (source.parse_provenance or {}).get("knowledge_wiki_policy")
    if wiki_policy is not None:
        fingerprint["knowledge_wiki_policy_hash"] = digest(wiki_policy)
    return fingerprint


def make_bundle(source: Any, artifact: dict, chunk_set: Any) -> dict:
    manifest = chunk_set.chunk_config.get("_manifest", [])
    bundle = {"version": BUNDLE_VERSION, "chunk_structure_version": CHUNK_VERSION,
            **source_fingerprint(source, artifact), "manifest_hash": digest(manifest),
            "config_hash": chunk_set.config_hash, "chunk_strategy": chunk_set.chunk_strategy}
    wiki = (chunk_set.chunk_config or {}).get("_knowledge_wiki")
    if wiki is not None:
        bundle["knowledge_wiki_hash"] = wiki.get("sha256")
    return bundle


def validate_chunk_set(source: Any, artifact: dict, chunk_set: Any) -> dict:
    config = chunk_set.chunk_config or {}
    bundle = config.get("_bundle")
    manifest = config.get("_manifest", [])
    expected = make_bundle(source, artifact, chunk_set)
    wiki = config.get("_knowledge_wiki")
    if wiki is not None:
        from app.modules.knowledge.services.wiki_compiler import validate_wiki_bundle

        validate_wiki_bundle(wiki, source, wiki.get("collection_id", ""))
    valid = (chunk_set.source_revision_id == source.id and chunk_set.status == "ready"
             and bundle == expected and config.get("_bundle_hash") == digest(expected)
             and chunk_set.manifest_hash == expected["manifest_hash"]
             and chunk_set.chunk_count == len(manifest) and chunk_set.fact_count == len(artifact["facts"])
             and config.get("_unit_manifest_hash") == expected["unit_manifest_hash"]
             and config.get("_fact_set_hash") == expected["fact_set_hash"] and bool(manifest))
    for number, item in enumerate(manifest):
        valid = valid and (item.get("index") == number
                           and item.get("chunk_hash") == hashlib.sha256(item.get("content", "").encode()).hexdigest())
    if not valid:
        raise AppException("Chunks không khớp bản nguồn đã duyệt; cần dựng lại chỉ mục.",
                           code="DERIVED_BUNDLE_INVALID", status_code=409)
    return expected


async def validate_index_bundle(db: Any, index: Any, source: Any, artifact: dict) -> str | None:
    """Check stored DB chunks against the sealed manifest before any pointer swap."""
    from sqlalchemy import select

    from app.modules.knowledge.models import KnowledgeBinding, KnowledgeChunk, KnowledgeChunkSet

    report = index.parity_report or {}
    chunk_set = await db.get(KnowledgeChunkSet, index.chunk_set_id) if index.chunk_set_id else None
    sealed = chunk_set and (chunk_set.chunk_config or {}).get("_bundle")
    if not sealed and not report.get("derived_bundle_hash"):
        return  # Historical builds remain readable, never silently upgraded.
    if not chunk_set:
        raise AppException("Thiếu tập đoạn đã ghim theo revision.", code="DERIVED_BUNDLE_INVALID", status_code=409)
    await db.refresh(source, with_for_update=True)
    await db.refresh(chunk_set, with_for_update=True)
    # Re-read the artifact after refresh rather than validating a stale identity-map value.
    from app.modules.knowledge.services.source_artifact import (
        get_source_artifact,
        get_structured_review_state,
    )

    artifact = get_source_artifact(source)
    if (source.parse_provenance or {}).get("automatic_ingestion"):
        from app.modules.knowledge.services.automatic_ingestion import verify_content_source
        await verify_content_source(source)
    if (source.parse_provenance or {}).get("canonical_format") == "qnu-rag-projection/v1":
        from app.modules.knowledge.services.qnu_serving import verify_revision_pair
        from app.modules.knowledge.services.semantic_store import verify_effective_projection

        document = await verify_revision_pair(source)
        await verify_effective_projection(source, artifact, document)
    if source.status != "ready" or get_structured_review_state(source)[1]:
        raise AppException("Nguồn cần duyệt lại.", code="SOURCE_NOT_READY", status_code=409)
    bundle = validate_chunk_set(source, artifact, chunk_set)
    binding = await db.get(KnowledgeBinding, index.binding_id)
    if (not binding or source.binding_id != index.binding_id or report.get("derived_bundle_hash") != digest(bundle)
            or report.get("derived_bundle_version") != BUNDLE_VERSION or not report.get("parity_passed")
            or report.get("expected_count") != chunk_set.chunk_count
            or report.get("verified_count") != chunk_set.chunk_count
            or report.get("knowledge_wiki") != (chunk_set.chunk_config or {}).get("_knowledge_wiki")):
        raise AppException("Vector không khớp tập dẫn xuất đã duyệt.", code="DERIVED_BUNDLE_INVALID", status_code=409)
    chunks = list((await db.execute(select(KnowledgeChunk).where(
        KnowledgeChunk.index_revision_id == index.id,
    ).order_by(KnowledgeChunk.chunk_index).with_for_update().execution_options(populate_existing=True))).scalars().all())
    manifest = chunk_set.chunk_config["_manifest"]
    valid = len(chunks) == len(manifest) == index.chunk_count
    for chunk, item in zip(chunks, manifest, strict=False):
        meta = chunk.chunk_metadata or {}
        valid = valid and (chunk.binding_id == index.binding_id and chunk.collection_id == binding.collection_id
                           and chunk.chunk_index == item["index"] and chunk.content == item["content"]
                           and chunk.chunk_hash == item["chunk_hash"] and chunk.page_number == item.get("page_number")
                           and chunk.section == item.get("section") and chunk.token_count == item.get("token_count", 0)
                           and meta.get("source_revision_id") == source.id and meta.get("chunk_set_id") == chunk_set.id
                           and all(meta.get(key) == value for key, value in item.get("metadata", {}).items()))
    if not valid:
        raise AppException("Chunks lưu trữ khác tập đã đối soát.", code="DERIVED_BUNDLE_INVALID", status_code=409)
    return binding.collection_id
