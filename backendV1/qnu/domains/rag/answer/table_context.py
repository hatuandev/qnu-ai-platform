"""Conservative reading dependencies for numbered native tables across page breaks."""

from itertools import pairwise

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.index.table_dependencies import (  # noqa: F401
    BASIS,
    TYPED_BASIS,
    adjoining,
    dependencies,
    header_row,
    multitier_header,
    sequence,
    typed_header,
)
from qnu.domains.knowledge.publication.evidence import assert_pinned, load_bundle
from qnu.domains.knowledge.publication.models import CompiledVersion
from qnu.platform.errors import Conflict

# Answer-time fallback only: unnumbered or merged-cell tables the index proof
# cannot chain still continue across one page edge by geometry and page band.
PAGE_BAND_BASIS = "native_page_band_continuation/v1"
BOTTOM_BAND = 0.88
TOP_BAND = 0.12
ALIGN_TOLERANCE = 0.005
STACK_TOLERANCE = 0.002


def _serving_table(block: dict, page: dict) -> dict | None:
    table = block.get("table")
    if (
        not table
        or page.get("extraction_method") != "native"
        or block.get("requires_review")
        or table.get("status") != "parsed"
        or not block.get("bbox")
        or block["bbox"].get("units") != "normalized_0_1"
    ):
        return None
    return block


def _ends_above(block: dict, top: float) -> bool:
    box = block.get("bbox") or {}
    return box.get("units") == "normalized_0_1" and box["y1"] <= top + STACK_TOLERANCE


def _opens_table(block: dict) -> bool:
    table = block["table"]
    return header_row(table) or typed_header(table) or multitier_header(table) is not None


def page_continuations(document: dict, proven: dict[str, dict]) -> dict[str, dict]:
    """Page-band links only where the numbered/typed/multi-tier proof is silent.

    A table block ending at the bottom band as the page's last block pairs with
    the next page's first table block when it opens the top band, nothing else
    sits above it, both boxes align horizontally and column counts match. The
    right block must not open a table of its own. A continuation is a reading
    dependency, never a new header proof: catalog still refuses unresolved
    headers and answers must quote those cells verbatim.
    """
    run = document["ocr_run_id"]
    result = {}
    pages = document["pages"]
    for left_page, right_page in pairwise(pages):
        if right_page.get("page_number") != left_page.get("page_number") + 1:
            continue
        left_blocks, right_blocks = left_page["blocks"], right_page["blocks"]
        if not left_blocks:
            continue
        left = _serving_table(left_blocks[-1], left_page)
        if left is None or left["bbox"]["y1"] < BOTTOM_BAND:
            continue
        opening = next((i for i, block in enumerate(right_blocks) if block.get("table")), None)
        if opening is None:
            continue
        right = _serving_table(right_blocks[opening], right_page)
        if right is None or right["bbox"]["y0"] > TOP_BAND:
            continue
        if not all(_ends_above(block, right["bbox"]["y0"]) for block in right_blocks[:opening]):
            continue
        left_ref = run + ":" + left["evidence_id"]
        right_ref = run + ":" + right["evidence_id"]
        a, b = left["bbox"], right["bbox"]
        if (
            left_ref in proven
            or right_ref in proven
            or abs(a["x0"] - b["x0"]) > ALIGN_TOLERANCE
            or abs(a["x1"] - b["x1"]) > ALIGN_TOLERANCE
            or left["table"]["column_count"] != right["table"]["column_count"]
            or _opens_table(right)
        ):
            continue
        result[left_ref] = {
            "basis": PAGE_BAND_BASIS,
            "header": left_ref,
            "chain": [left_ref],
            "previous": None,
        }
        result[right_ref] = {
            "basis": PAGE_BAND_BASIS,
            "header": left_ref,
            "chain": [left_ref, right_ref],
            "previous": left_ref,
        }
    return result


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
            links = dependencies(document)
            for ref, link in page_continuations(document, links).items():
                links.setdefault(ref, link)
            result.update({(binding.id, ref): link for ref, link in links.items()})
    return result
