"""Conservative reading dependencies for numbered native tables across page breaks."""

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.index.table_dependencies import (  # noqa: F401
    BASIS,
    adjoining,
    dependencies,
    header_row,
    sequence,
)
from qnu.domains.knowledge.publication.evidence import assert_pinned, load_bundle
from qnu.domains.knowledge.publication.models import CompiledVersion
from qnu.platform.errors import Conflict


async def bound_dependencies(
    db, blob, allowed, rows: list[IndexChunk]
) -> dict[tuple[str, str], dict]:
    """Only pinned, serving publications; never read a client-supplied source path."""
    result = {}
    for binding in allowed:
        if not any(r.input_id == binding.id and r.kind == "table" for r in rows):
            continue
        version = await db.get(CompiledVersion, binding.version_id)
        if version is None:
            raise Conflict("Phiên bản nguồn không còn khả dụng.", code="answer_evidence_changed")
        bundle = await load_bundle(
            db,
            blob,
            binding.workspace_id,
            binding.collection_id,
            version.compilation_run_id,
            require_current=True,
            serving=True,
        )
        assert_pinned(version, bundle)
        for document in bundle.documents:
            result.update({(binding.id, ref): link for ref, link in dependencies(document).items()})
    return result
