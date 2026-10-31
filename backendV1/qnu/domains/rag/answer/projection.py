"""Lossless prompt projection shared by context budgeting and answer generation."""

from qnu.domains.knowledge.index.presentation import reading_text
from qnu.domains.knowledge.index.schemas import SearchHit


def evidence_item(hit: SearchHit, evidence_id: str) -> dict:
    item = {"evidence_id": evidence_id, "kind": hit.kind, "text": reading_text(hit)}
    if not hit.structure:
        return item
    item["structure"] = hit.structure
    return item
