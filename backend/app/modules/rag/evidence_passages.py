"""Server-owned source passages: models select IDs instead of reproducing quotes."""

import re
from itertools import pairwise
from typing import Literal

from pydantic import Field, create_model

from app.modules.rag.evidence_context import omit_empty_fields
from app.modules.rag.evidence_dependencies import dependency_intros, sentence_continuations
from app.modules.rag.evidence_schemas import (
    AnswerProposal,
    EvidenceBlock,
    EvidenceClaim,
    QuoteReference,
    StrictContract,
)
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.source_row_context import model_position, table_row_context


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
    evidence_ids: list[str] = Field(min_length=1, max_length=12)
    context_ids: list[str] = Field(default_factory=list, max_length=3)


class PassageProposal(StrictContract):
    status: str = Field(pattern="^(supported|partial|missing|conflict|clarify)$")
    claims: list[PassageClaim] = Field(default_factory=list, max_length=12)
    missing_constraints: list[str] = Field(default_factory=list, max_length=10)


def proposal_contract(catalog):
    allowed = Literal[tuple(catalog)]
    claim = create_model("SourcePassageClaim", __base__=PassageClaim,
        evidence_ids=(list[allowed], Field(min_length=1, max_length=12)),
        context_ids=(list[allowed], Field(default_factory=list, max_length=3)))
    return create_model("SourcePassageProposal", __base__=PassageProposal,
        claims=(list[claim], Field(default_factory=list, max_length=12)))


def passage_catalog(blocks):
    catalog = {}
    for index, block in enumerate(blocks, 1):
        # Keep punctuation, decimal values and formulas intact in every raw span.
        starts = [0, *[m.end() for m in re.finditer(r"(?<!\d\.)(?<=[.!?;])\s+(?=[A-ZÀ-Ỹ])", block.text)], len(block.text)]
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
             **({'table_row': row} if (row := table_row_context(by_id[ref.block_id])) else {}),
             "source_revision_id": by_id[ref.block_id].source_revision_id,
             **model_position(by_id[ref.block_id].section, row),
             "title": by_id[ref.block_id].title,
             "record_label": by_id[ref.block_id].record_label,
             "record_path": by_id[ref.block_id].record_path,
             "fact_context": by_id[ref.block_id].fact_context,
             "temporal_scope": by_id[ref.block_id].temporal_scope.model_dump()} for pid, ref in catalog.items()]


def compact_passage_payload(blocks, catalog):
    """Same IDs and exact sentences; whole-body ID is an alias, not copied text."""
    grouped, whole_quotes = {}, {}
    for passage in passage_payload(blocks, catalog):
        block_id = catalog[passage["id"]].block_id
        entry = grouped.setdefault(block_id, {key: value for key, value in passage.items()
            if key not in {"id", "text"}} | {"passages": []})
        if "." not in passage["id"]:
            entry["whole_passage_id"] = passage["id"]
            whole_quotes[block_id] = passage["text"]
        else:
            entry["passages"].append({"id": passage["id"], "text": passage["text"]})
    for block_id, quote in whole_quotes.items():
        entry = grouped[block_id]
        parts = " ".join(part["text"] for part in entry["passages"])
        if re.sub(r"\s+", " ", quote).strip() != re.sub(r"\s+", " ", parts).strip():
            # The catalog intentionally omits sentence fragments shorter than
            # three characters. Never lose those characters from a whole ID.
            entry["whole_text"] = quote
    return omit_empty_fields(list(grouped.values()))


def resolve_proposal(proposal: PassageProposal, catalog, blocks: list[EvidenceBlock] | None = None,
                     *, separate_context: bool = False) -> AnswerProposal:
    claims = []
    for claim in proposal.claims:
        if separate_context:
            # A public sentence and its context are different roles. Never turn
            # a cited heading/date/adjacent event into another public assertion.
            valid = all(pid in catalog for pid in [*claim.evidence_ids, *claim.context_ids])
            context = [catalog[pid] for pid in dict.fromkeys(claim.context_ids)] if valid else []
            for index, pid in enumerate(dict.fromkeys(claim.evidence_ids)):
                body = catalog[pid] if valid else QuoteReference(block_id="invalid", quote="unknown passage")
                refs = [body, *[ref for ref in context if ref != body]]
                claims.append(EvidenceClaim(id=f"{claim.id}.body{index}", text=body.quote, references=refs))
            continue
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
            if len(groups) > 1 or len(references) > 4:
                # The selector may identify a whole multi-item list. Preserve
                # EVERY selected proof, splitting extractive claims into bounded
                # same-source reference groups instead of dropping a fifth ID.
                for index, refs in enumerate(groups.values(), 1):
                    for offset in range(0, len(refs), 4):
                        group = refs[offset:offset + 4]
                        claims.append(EvidenceClaim(id=f"{claim.id}.source{index}.part{offset // 4}",
                            text=group[0].quote, references=group))
                continue
        # Draft prose is not evidence and is never published. Binding checks the
        # actual selected sentence; invented numbers in a label cannot reject or
        # contaminate an otherwise valid extractive answer.
        claims.append(EvidenceClaim(id=claim.id, text=references[0].quote, references=references))
    return AnswerProposal(status=proposal.status, claims=claims, missing_constraints=proposal.missing_constraints)


def source_grounded_claims(claims: list[dict], blocks: list[EvidenceBlock], *, primary_only: bool = False) -> list[dict]:
    """Publish selected source sentences, not a lossy paraphrase of conditions."""
    by_id = {block.id: block for block in blocks}
    intros = dependency_intros(blocks)
    result, seen = [], set()
    for claim in claims:
        primary = claim['references'][0]
        body = by_id[primary['block_id']]
        if body.fact_context.get('source_kind') == 'list':
            # A sentence inside one native list item cannot silently drop that
            # item's following qualification. Never expand to a sibling item.
            items = list(re.finditer(r'(?m)^\s*(?:\d+|[a-z])[.)]\s+.*(?:\n(?!\s*(?:\d+|[a-z])[.)]\s).*?)*', body.text))
            matches = [m.group().strip() for m in items if primary['quote'] in m.group()]
            if len(matches) == 1 and len(matches[0]) <= 4000:
                expanded = bind_quote(QuoteReference(block_id=body.id, quote=matches[0]), by_id)
                claim = {**claim, 'text': expanded['quote'], 'references': [expanded, *claim['references'][1:]]}
        parents = [bind_quote(QuoteReference(block_id=parent.id, quote=parent.text), by_id)
                   for ref in claim["references"] for parent in intros.get(ref["block_id"], [])]
        continuations = [bind_quote(QuoteReference(block_id=block.id, quote=block.text), by_id)
                         for ref in claim["references"]
                         for block in sentence_continuations(blocks, by_id[ref["block_id"]])]
        references = list({(ref["block_id"], ref["start"], ref["end"], ref["quote"]): ref
                           for ref in [*parents, *claim["references"], *continuations]}.values())
        for part, reference in enumerate(references, 1):
            if primary_only and reference != claim["references"][0]:
                continue
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
