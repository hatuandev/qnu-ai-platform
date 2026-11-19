"""Read exact cited passages from pinned OCR, retaining the compiled search text."""

from sqlalchemy import select

from qnu.domains.knowledge.models import KBSource
from qnu.domains.knowledge.publication.evidence import assert_pinned, load_bundle
from qnu.domains.knowledge.publication.models import CompiledVersion
from qnu.platform.errors import Conflict


def passages(source, documents):
    result = []
    for doc in documents:
        run = doc["ocr_run_id"]
        position = 0
        for page in doc["pages"]:
            for block in page["blocks"]:
                ref = run + ":" + block["evidence_id"]
                if ref in source.citations and not block.get("table") and block.get("text"):
                    result.append(
                        {"citation": ref, "text": block["text"], "position": str(position)}
                    )
                # Count every block, including uncited blocks and tables: a gap
                # must never be represented as a verified narrative continuation.
                position += 1
    return result


async def pinned_bundles(db, blob, workspace_id, collection_id, sources, bundles=None):
    """Request-local cache only; every bundle still uses the published snapshot checks."""
    bundles = bundles if bundles is not None else {}
    for source in sources:
        if source.version_id in bundles:
            continue
        version = await db.get(CompiledVersion, source.version_id)
        if version is None or version.document_id != source.document_id:
            raise Conflict("Nguồn đã thay đổi.", code="answer_evidence_changed")
        bundle = await load_bundle(
            db,
            blob,
            workspace_id,
            collection_id,
            version.compilation_run_id,
            require_current=True,
            serving=True,
        )
        assert_pinned(version, bundle)
        bundles[source.version_id] = bundle
    return bundles


async def _source_titles(db, workspace_id, collection_id, sources) -> dict[str, str]:
    document_ids = sorted({source.document_id for source in sources})
    if not document_ids:
        return {}
    rows = await db.execute(
        select(KBSource.id, KBSource.title).where(
            KBSource.id.in_(document_ids),
            KBSource.workspace_id == workspace_id,
            KBSource.collection_id == collection_id,
        )
    )
    return dict(rows.all())


async def attach_source_text(
    db, blob, workspace_id, collection_id, sources, *, scope=None, bundles=None
):
    # Caller has authorized and validated the retrieved snapshot. No arbitrary
    # page neighbors: only block IDs already cited by the published chunk.
    # ``scope`` names the owning collection when one answer spans several.
    bundles = bundles if bundles is not None else {}
    groups: dict[str, list] = {}
    for source in sources:
        owner = (scope or {}).get(source.chunk_id, collection_id)
        groups.setdefault(owner, []).append(source)
    titles = {}
    for owner, group in groups.items():
        await pinned_bundles(
            db, blob, workspace_id, owner, [s for s in group if s.kind != "table"], bundles
        )
        titles.update(await _source_titles(db, workspace_id, owner, group))
    for source in sources:
        source.source_title = titles.get(source.document_id)
        if source.kind in {"table", "row_card"}:
            continue
        source.source_passages = passages(source, bundles[source.version_id].documents)
    return sources
