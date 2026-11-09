"""Compact prompt projection; full geometry and provenance remain server-side."""

from qnu.domains.knowledge.index.presentation import reading_text, table_prefix
from qnu.domains.knowledge.index.schemas import SearchHit

PAYLOAD_VERSION = "qnu.answer-payload/v2"


def source_code(source: SearchHit, codes: dict) -> str:
    key = (source.document_id, source.version_id, source.publication_decision_id)
    if key not in codes:
        codes[key] = f"S{len(codes) + 1}"
    return codes[key]


def evidence_item(
    hit: SearchHit,
    evidence_id: str,
    *,
    selectable: bool = False,
    source_codes: dict | None = None,
    passages: list[dict] | None = None,
    same_as: str | None = None,
) -> dict:
    item = {"id": evidence_id, "kind": hit.kind}
    if source_codes is not None:
        item["src"] = source_code(hit, source_codes)
    if same_as is not None:
        item["same"] = same_as
        return item
    if hit.kind == "table":
        prefix = table_prefix(hit)
        if selectable and prefix is not None:
            # Cell values appear once in the table catalog; the title is the
            # only reading context the model needs for this fragment.
            item["title"] = prefix.rstrip()
        else:
            item["text"] = reading_text(hit)
            if (hit.structure or {}).get("table_status"):
                item["table_status"] = hit.structure["table_status"]
        return item
    selected = passages if passages is not None else getattr(hit, "source_passages", [])
    # Exact cited source takes precedence over a compiler paraphrase that may
    # have dropped a condition. Each passage is sent exactly once.
    item["text"] = "\n".join(p["text"] for p in selected) if selected else reading_text(hit)
    return item
