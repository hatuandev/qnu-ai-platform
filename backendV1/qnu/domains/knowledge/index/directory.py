"""Database-only readiness preview for the public directory."""

from collections import defaultdict

from sqlalchemy import literal, select, tuple_, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.index.models import IndexInput, IndexRun
from qnu.domains.knowledge.publication.models import CompiledVersion
from qnu.domains.lifecycle.guards import visible

CollectionScope = tuple[str, str]
VersionIdentity = tuple[str, str, str, int]


async def directory_ready(db: AsyncSession, scopes: set[CollectionScope]) -> set[CollectionScope]:
    if not scopes:
        return set()
    published = select(
        literal("published"),
        CompiledVersion.workspace_id,
        CompiledVersion.collection_id,
        CompiledVersion.document_id,
        CompiledVersion.id,
        CompiledVersion.bundle_sha256,
        CompiledVersion.state_version,
    ).where(
        tuple_(CompiledVersion.workspace_id, CompiledVersion.collection_id).in_(scopes),
        CompiledVersion.status == "published",
        visible("document", CompiledVersion.document_id),
    )

    indexed = (
        select(
            literal("indexed"),
            IndexRun.workspace_id,
            IndexRun.collection_id,
            IndexInput.document_id,
            IndexInput.version_id,
            IndexInput.bundle_sha256,
            IndexInput.version_state,
        )
        .join(IndexInput, IndexInput.run_id == IndexRun.id)
        .where(
            tuple_(IndexRun.workspace_id, IndexRun.collection_id).in_(scopes),
            IndexRun.is_active.is_(True),
            IndexRun.status == "completed",
            IndexRun.manifest_key.is_not(None),
            IndexRun.manifest_sha256.is_not(None),
        )
    )
    current: dict[CollectionScope, set[VersionIdentity]] = defaultdict(set)
    served: dict[CollectionScope, set[VersionIdentity]] = defaultdict(set)
    for source, workspace, collection, document, version, digest, state in await db.execute(
        union_all(published, indexed)
    ):
        versions = current if source == "published" else served
        versions[workspace, collection].add((document, version, digest, state))
    return {scope for scope, versions in current.items() if versions == served.get(scope)}
