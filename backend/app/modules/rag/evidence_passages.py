"""Server-owned source passages: models select IDs instead of reproducing quotes."""

import re
from itertools import pairwise
from typing import Literal

from pydantic import Field, create_model

from app.modules.rag.evidence_dependencies import dependency_intros, sentence_continuations
from app.modules.rag.evidence_schemas import (
    AnswerProposal,
    EvidenceBlock,
    EvidenceClaim,
    QuoteReference,
    StrictContract,
)
from app.modules.rag.evidence_validation import bind_quote


def context_only(block: EvidenceBlock) -> bool:
    if block.is_container or re.fullmatch(r"\s*#{1,6}\s+[^\n]+\s*", block.text):
        return True
    if not re.fullmatch(r"\s*\*\*[^*\n]+\*\*\s*", block.text):
        return False
    # Bold styling alone is not a heading: labeled scalar fields and numeric
    # summaries remain answer-bearing evidence. A bare year title stays context.
    if re.search(r":\s*[^*:\s]", block.text):
        return False
    numbers = re.findall(r"\d+(?:[.,]\d+)*", block.text)
    return not any(not re.fullmatch(r"(?:19|20)\d{2}", value) for value in numbers)


class PassageClaim(StrictContract):
    id: str
    text: str = Field(min_length=3, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1, max_length=4)


class PassageProposal(StrictContract):
    status: str = Field(pattern="^(supported|partial|missing|conflict|clarify)$")
    claims: list[PassageClaim] = Field(default_factory=list, max_length=12)
    missing_constraints: list[str] = Field(default_factory=list, max_length=10)


def proposal_contract(catalog):
    allowed = Literal[tuple(catalog)]
    claim = create_model("SourcePassageClaim", __base__=PassageClaim,
        evidence_ids=(list[allowed], Field(min_length=1, max_length=4)))
    return create_model("SourcePassageProposal", __base__=PassageProposal,
        claims=(list[claim], Field(default_factory=list, max_length=12)))


def passage_catalog(blocks):
    catalog = {}
    for index, block in enumerate(blocks, 1):
        # Keep punctuation, decimal values and formulas intact in every raw span.
        starts = [0, *[m.end() for m in re.finditer(r"(?<=[.!?;])\s+(?=[A-ZÀ-Ỹ])", block.text)], len(block.text)]
        for part, (start, end) in enumerate(pairwise(starts), 1):
            quote = block.text[start:end].strip()
            if len(quote) >= 3:
                catalog[f"e{index}.{part}"] = QuoteReference(block_id=block.id, quote=quote)
        if len(block.text) <= 4000:
            catalog[f"e{index}"] = QuoteReference(block_id=block.id, quote=block.text)
    return catalog


def passage_payload(blocks, catalog):
    by_id = {block.id: block for block in blocks}
    return [{"id": pid, "text": ref.quote,
             "source_revision_id": by_id[ref.block_id].source_revision_id,
             "section": by_id[ref.block_id].section,
             "title": by_id[ref.block_id].title,
             "record_label": by_id[ref.block_id].record_label,
             "record_path": by_id[ref.block_id].record_path,
             "fact_context": by_id[ref.block_id].fact_context,
             "temporal_scope": by_id[ref.block_id].temporal_scope.model_dump()} for pid, ref in catalog.items()]


def resolve_proposal(proposal: PassageProposal, catalog, blocks: list[EvidenceBlock] | None = None) -> AnswerProposal:
    claims = []
    for claim in proposal.claims:
        if any(pid not in catalog for pid in claim.evidence_ids):
            # Never silently bind an unknown ID to arbitrary evidence.
            references = [QuoteReference(block_id="invalid", quote="unknown passage")]
        else:
            references = [catalog[pid] for pid in dict.fromkeys(claim.evidence_ids)]
        if blocks and all(ref.block_id != "invalid" for ref in references):
            # Split extractive claims by source; never let one source supply scope
            # for another. Each result still passes binding AND semantic verification.
            by_block = {block.id: block for block in blocks}
            groups = {}
            for ref in references:
                block = by_block[ref.block_id]
                identity = (block.binding_id, block.index_revision_id, block.source_revision_id, block.canonical_hash)
                groups.setdefault(identity, []).append(ref)
            if len(groups) > 1:
                claims.extend(EvidenceClaim(id=f"{claim.id}.source{index}", text=refs[0].quote, references=refs)
                              for index, refs in enumerate(groups.values(), 1))
                continue
        # Draft prose is not evidence and is never published. Binding checks the
        # actual selected sentence; invented numbers in a label cannot reject or
        # contaminate an otherwise valid extractive answer.
        claims.append(EvidenceClaim(id=claim.id, text=references[0].quote, references=references))
    return AnswerProposal(status=proposal.status, claims=claims, missing_constraints=proposal.missing_constraints)


def source_grounded_claims(claims: list[dict], blocks: list[EvidenceBlock]) -> list[dict]:
    """Publish selected source sentences, not a lossy paraphrase of conditions."""
    by_id = {block.id: block for block in blocks}
    intros = dependency_intros(blocks)
    result, seen = [], set()
    for claim in claims:
        parents = [bind_quote(QuoteReference(block_id=parent.id, quote=parent.text), by_id)
                   for ref in claim["references"] for parent in intros.get(ref["block_id"], [])]
        continuations = [bind_quote(QuoteReference(block_id=block.id, quote=block.text), by_id)
                         for ref in claim["references"]
                         for block in sentence_continuations(blocks, by_id[ref["block_id"]])]
        references = list({(ref["block_id"], ref["start"], ref["end"], ref["quote"]): ref
                           for ref in [*parents, *claim["references"], *continuations]}.values())
        for part, reference in enumerate(references, 1):
            block = by_id[reference["block_id"]]
            if context_only(block):
                continue
            identity = tuple(reference.get(key) for key in ("binding_id", "index_revision_id",
                "source_revision_id", "canonical_hash", "origin", "fact_id", "start", "end", "quote"))
            if identity in seen:
                continue
            seen.add(identity)
            result.append({**claim, "id": f"{claim['id']}.{part}", "text": reference["quote"],
                "references": [reference, *[ref for ref in references if ref is not reference]]})
    # Remove a sentence only when a selected larger span contains it in the SAME
    # immutable source. Numeric/year similarity across revisions is not duplication.
    return [claim for i, claim in enumerate(result) if not any(
        i != j and _contains(other["references"][0], claim["references"][0])
        for j, other in enumerate(result))]


def _contains(outer: dict, inner: dict) -> bool:
    keys = ("binding_id", "index_revision_id", "source_revision_id", "canonical_hash", "origin")
    if any(outer.get(key) != inner.get(key) for key in keys) or inner.get("origin") != "canonical":
        return False
    if any(ref.get(key) is None for ref in (outer, inner) for key in ("start", "end")):
        return False
    return (outer["start"] <= inner["start"] and inner["end"] <= outer["end"]
            and (outer["start"], outer["end"]) != (inner["start"], inner["end"]) and inner["quote"] in outer["quote"])
