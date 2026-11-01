"""Lossless prompt projection shared by context budgeting and answer generation."""

from qnu.domains.knowledge.index.presentation import reading_text
from qnu.domains.knowledge.index.schemas import SearchHit


def evidence_item(hit: SearchHit, evidence_id: str) -> dict:
    item = {
        "evidence_id": evidence_id,
        "kind": hit.kind,
        "source_identity": [hit.document_id, hit.version_id, hit.publication_decision_id],
        "text": reading_text(hit),
    }
    passages = getattr(hit, "source_passages", [])
    if passages:
        # Search/index bytes remain untouched; exact cited source takes precedence
        # over a compiler paraphrase that may have dropped a condition.
        item["text"] = "\n".join(p["text"] for p in passages)
        item["source_passage_refs"] = [p["citation"] for p in passages]
    if not hit.structure:
        return item
    # Search enrichment is a derived index view, not additional source evidence.
    # Do not duplicate the original body or full glossary in the answer budget.
    item["structure"] = {k: v for k, v in hit.structure.items() if k != "search_context"}
    return item
