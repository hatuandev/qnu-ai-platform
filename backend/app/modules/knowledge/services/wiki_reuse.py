"""Reuse compatible wiki derivatives with new revision provenance, never old IDs."""

import asyncio
from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeChunkSet, KnowledgeSourceRevision
from app.modules.knowledge.services.derived_bundle import source_fingerprint, validate_chunk_set
from app.modules.knowledge.services.source_artifact import get_source_artifact
from app.modules.knowledge.services.wiki_compiler import (
    digest,
    source_identity,
    validate_wiki_bundle,
)
from app.modules.knowledge.wiki_schemas import WikiPage, WikiPolicy

REUSE_VERSION = "qnu-wiki-reuse/v1"


def compatible_source(source: Any) -> dict:
    fingerprint = source_fingerprint(source, get_source_artifact(source))
    return {k: v for k, v in fingerprint.items() if k != "source_revision_id"}


def rebind_wiki(bundle: dict, previous: Any, source: Any, collection_id: str) -> dict:
    validate_wiki_bundle(bundle, previous, collection_id)
    if (previous.binding_id != source.binding_id or compatible_source(previous) != compatible_source(source)
            or bundle["status"] != "ready"
            or WikiPolicy.model_validate(bundle["policy"]) != WikiPolicy.model_validate(
                source.parse_provenance["knowledge_wiki_policy"])):
        raise ValueError("WIKI_REUSE_INCOMPATIBLE")
    identity = source_identity(source, collection_id)
    rebound = deepcopy(bundle)
    rebound.update(identity)
    from app.modules.knowledge.services.wiki_inventory import stored_pages
    groups = {}
    for stored in rebound['pages']:
        key = stored['kind'], stored['title']
        page = WikiPage.model_validate({k: stored[k] for k in ('kind', 'title', 'sections')})
        if key not in groups:
            groups[key] = page
        else:
            groups[key] = groups[key].model_copy(update={'sections': [*groups[key].sections, *page.sections]})
    rebound['pages'] = stored_pages(groups, identity)
    rebound.update(calls=0, contract_retries=0, input_source_chars=0, model_calls=[],
        reuse={"version": REUSE_VERSION, "from_source_revision_id": previous.id,
               "from_bundle_sha256": bundle["sha256"], "compatible_fingerprint": digest(compatible_source(source))})
    rebound["sha256"] = digest({k: v for k, v in rebound.items() if k != "sha256"})
    validate_wiki_bundle(rebound, source, collection_id)
    return rebound


async def find_reusable_wiki(db: AsyncSession, source: Any, collection_id: str,
                             config_hash: str) -> dict | None:
    rows = (await db.execute(select(KnowledgeSourceRevision, KnowledgeChunkSet)
        .join(KnowledgeChunkSet, KnowledgeChunkSet.source_revision_id == KnowledgeSourceRevision.id)
        .where(KnowledgeSourceRevision.binding_id == source.binding_id,
            KnowledgeSourceRevision.id != source.id, KnowledgeSourceRevision.status == "ready",
            KnowledgeChunkSet.status == "ready", KnowledgeChunkSet.config_hash == config_hash)
        .order_by(KnowledgeSourceRevision.revision_no.desc()).limit(1))).all()
    for previous, chunks in rows:
        bundle = (chunks.chunk_config or {}).get("_knowledge_wiki")
        if not bundle or bundle.get("status") != "ready":
            continue
        # Corruption is an error, never an excuse to silently regenerate or serve stale content.
        return await asyncio.to_thread(validated_rebind, bundle, previous, chunks, source, collection_id)
    return None


def validated_rebind(bundle: dict, previous: Any, chunks: Any, source: Any, collection_id: str) -> dict:
    validate_chunk_set(previous, get_source_artifact(previous), chunks)
    return rebind_wiki(bundle, previous, source, collection_id)
