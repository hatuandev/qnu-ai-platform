"""Reading order for already retrieved, cited source blocks; no source expansion."""

from qnu.domains.rag.answer.schemas import EvidenceSource


def continuation_supports(sources: list[EvidenceSource]) -> dict[str, list[str]]:
    """Complete a clipped leading line using its immediately preceding cited line."""
    blocks, first = {}, {}
    for source in sources:
        if source.kind == "table":
            continue
        for passage in source.source_passages:
            ref, pos = passage["citation"], passage.get("position", "")
            if ref not in source.citations or not pos.isdecimal():
                continue
            identity = (
                source.document_id,
                source.version_id,
                source.publication_decision_id,
                ref.split(":", 1)[0],
            )
            key = (*identity, int(pos))
            blocks.setdefault(key, []).append((source.evidence_id, passage["text"]))
            if source.evidence_id not in first or key[-1] < first[source.evidence_id][0][-1]:
                first[source.evidence_id] = (key, passage["text"])
    supports = {}
    for owner, (key, text) in first.items():
        if not text.strip() or not text.lstrip()[0].islower():
            continue
        before = blocks.get((*key[:-1], key[-1] - 1), [])
        parents = [
            eid
            for eid, previous in before
            if eid != owner and previous.strip() and previous.rstrip()[-1] not in ".!?;:"
        ]
        if parents:
            supports[owner] = list(dict.fromkeys(parents))
    return supports


def complete_citations(statements, sources):
    supports = continuation_supports(sources)
    for statement in statements:
        ids = list(statement.evidence_ids)
        for eid in ids:
            ids.extend(parent for parent in supports.get(eid, []) if parent not in ids)
        statement.evidence_ids = ids
    return statements


def reading_order(sources: list[EvidenceSource]) -> list[list[str]]:
    """Verified contiguous runs by evidence ID only; text stays in each evidence item."""
    buckets = {}
    for source in sources:
        if source.kind == "table":
            continue
        for passage in source.source_passages:
            ref, position = passage["citation"], passage.get("position", "")
            if ref not in source.citations or not position.isdecimal():
                continue
            identity = (
                source.document_id,
                source.version_id,
                source.publication_decision_id,
                ref.split(":", 1)[0],
            )
            blocks = buckets.setdefault(identity, {})
            index = int(position)
            block = blocks.setdefault(index, {"citation": ref, "text": passage["text"], "ids": []})
            if block["citation"] != ref or block["text"] != passage["text"]:
                # Never expose an inferred relation for inconsistent source maps.
                return []
            if source.evidence_id not in block["ids"]:
                block["ids"].append(source.evidence_id)
    groups, current, previous = [], [], None
    for blocks in buckets.values():
        for index, block in sorted(blocks.items()):
            if previous is None or index != previous + 1:
                if len(current) > 1:
                    groups.append(current)
                current = []
            current = list(dict.fromkeys([*current, *block["ids"]]))
            previous = index
        if len(current) > 1:
            groups.append(current)
        current, previous = [], None
    return groups
