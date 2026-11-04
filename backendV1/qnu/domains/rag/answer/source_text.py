"""Read exact cited passages from pinned OCR, retaining the compiled search text."""

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


async def attach_source_text(db, blob, workspace_id, collection_id, sources, *, bundles=None):
    # Caller has authorized and validated the retrieved snapshot. No arbitrary
    # page neighbors: only block IDs already cited by the published chunk.
    bundles = await pinned_bundles(
        db, blob, workspace_id, collection_id, [s for s in sources if s.kind != "table"], bundles
    )
    for source in sources:
        if source.kind == "table":
            continue
        source.source_passages = passages(source, bundles[source.version_id].documents)
    return sources
