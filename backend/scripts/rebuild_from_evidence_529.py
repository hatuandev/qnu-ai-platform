"""Read-only A/B of the PDF builder: rebuild the standard from stored raw evidence and diff the counts.

Loads each revision's ``pdf-evidence-v1.json`` sidecar, runs the current builder over it in memory and
compares flag codes, block types and cell states with the stored ``qnu-doc-v1.json``. Writes no rows
and no files, and calls no OCR or model.
"""

import argparse
import asyncio
import json
import re
from collections import Counter
from difflib import SequenceMatcher

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.core.storage import storage_service
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuStructuredDocument,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document


def profile(document: QnuStructuredDocument) -> dict:
    flags: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    states: Counter[str] = Counter()
    for block in document.blocks:
        for flag in block.quality_flags:
            flags[flag.code] += 1
            statuses[f"{flag.code}:{flag.status}"] += 1
        fields = block.attributes.get("fields")
        if isinstance(fields, dict):
            for value in fields.values():
                if isinstance(value, dict):
                    states[str(value.get("state"))] += 1
    return {
        "blocks": len(document.blocks),
        "block_types": dict(Counter(block.type for block in document.blocks)),
        "flags": dict(flags),
        "flag_statuses": dict(statuses),
        "field_states": dict(states),
        "table_rows_with_alternatives": sum(
            1 for block in document.blocks if isinstance(block.source_data, dict)
            and block.source_data.get("alternatives")
        ),
        "visual_classification": document.document_meta.get("visual_classification"),
    }


def diff(old: dict, new: dict) -> dict:
    out = {"blocks": f"{old['blocks']} -> {new['blocks']}", "block_types": {}, "flags": {}, "field_states": {}}
    for key in ("block_types", "flags", "field_states"):
        for name in sorted(set(old[key]) | set(new[key])):
            before, after = old[key].get(name, 0), new[key].get(name, 0)
            if before != after:
                out[key][name] = f"{before} -> {after}"
    out["visual_classification"] = {"stored": old["visual_classification"], "rebuilt": new["visual_classification"]}
    return out


def words(document: QnuStructuredDocument, *, alternatives: bool = False) -> Counter[str]:
    """Every word token the document can serve, optionally including the losing representation."""
    parts = [block.body for block in document.blocks]
    if alternatives:
        for block in document.blocks:
            for item in (block.source_data or {}).get("alternatives", []) if isinstance(block.source_data, dict) else []:
                parts.append(str(item.get("text", "")))
                for row in (item.get("table") or {}).get("grid", []) if isinstance(item.get("table"), dict) else []:
                    parts.extend(cell.get("raw", "") for cell in row)
    return Counter(re.findall(r"\w+", " ".join(parts).casefold()))


def coverage(stored: QnuStructuredDocument, rebuilt: QnuStructuredDocument) -> dict:
    """Tokens the old standard served but the new one publishes nowhere, including alternative evidence."""
    missing = words(stored) - (words(rebuilt) | words(rebuilt, alternatives=True))
    return {"lost_token_instances": sum(missing.values()), "distinct_lost_tokens": len(missing),
            "lost_samples": [f"{token}×{count}" for token, count in missing.most_common(25)]}


def losing_cells(rebuilt: QnuStructuredDocument, markdown: str) -> list[dict]:
    """Non-empty cells of the representation the builder dropped that never reach the published text."""
    missing = []
    published = " ".join(markdown.casefold().split())
    for block in rebuilt.blocks:
        for item in (block.source_data or {}).get("alternatives", []) if isinstance(block.source_data, dict) else []:
            table = item.get("table") if isinstance(item, dict) else None
            for row in (table or {}).get("grid", []):
                for cell in row:
                    value = " ".join(str(cell.get("raw", "")).casefold().split())
                    if value and value not in published:
                        missing.append({"block_id": block.id, "origin": cell.get("origin"), "value": value[:120]})
    return missing


def grep_blocks(rebuilt: QnuStructuredDocument, needle: str) -> list[dict]:
    """Which published blocks carry a phrase, so a title or header can be traced after re-selection."""
    needle = " ".join(needle.casefold().split())
    return [{"id": block.id, "type": block.type, "page": block.source_locations[0].page,
             "flags": [flag.code for flag in block.quality_flags], "body": block.body[:160]}
            for block in rebuilt.blocks if needle in " ".join(block.body.casefold().split())]


def conflicts(rebuilt: QnuStructuredDocument) -> list[dict]:
    """Both sides of every kept conflict, to see how far the two readings really differ."""
    rows = []
    for block in rebuilt.blocks:
        if not any(flag.code == "native_ocr_conflict" for flag in block.quality_flags):
            continue
        alternatives = []
        for item in (block.source_data or {}).get("alternatives", []) if isinstance(block.source_data, dict) else []:
            text = item.get("text") if isinstance(item, dict) else None
            if not text and isinstance(item, dict) and isinstance(item.get("table"), dict):
                text = " | ".join(" ".join(cell["raw"] for cell in row) for row in item["table"]["grid"][:2])
            alternatives.append(" ".join(str(text).split())[:220])
        published = " ".join(block.body.split())[:220]
        rows.append({"id": block.id, "type": block.type, "published": published, "alternatives": alternatives,
                     "similarity": [round(SequenceMatcher(None, published.casefold(), text.casefold()).ratio(), 3)
                                    for text in alternatives]})
    return rows


def dump_blocks(rebuilt: QnuStructuredDocument, stored: QnuStructuredDocument) -> dict:
    """Every block of both versions, so a disappearing phrase can be traced to its representation."""
    def rows(document: QnuStructuredDocument) -> list[dict]:
        return [{"id": block.id, "type": block.type, "page": block.source_locations[0].page if block.source_locations else None,
                 "flags": [flag.code for flag in block.quality_flags], "body": " ".join(block.body.split())[:130]}
                for block in document.blocks if block.type != "table_row"]
    return {"rebuilt": rows(rebuilt), "stored": rows(stored)}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--revision", action="append", default=[])
    parser.add_argument("--full", action="store_true", help="In trọn profile bản dựng lại.")
    parser.add_argument("--coverage", action="store_true", help="Soi token mất giữa bản đã lưu và bản dựng lại.")
    parser.add_argument("--cells", action="store_true", help="In ô của bản thua không xuất hiện trong MD đã publish.")
    parser.add_argument("--grep", help="Khối nào trong bản dựng lại chứa cụm từ này.")
    parser.add_argument("--dump", action="store_true", help="In khối ngoài table_row của cả hai bản.")
    parser.add_argument("--conflicts", action="store_true", help="In cả hai phía của mỗi xung đột native/OCR.")
    args = parser.parse_args()

    async with AsyncSessionFactory() as db:
        query = (
            select(KnowledgeSourceRevision)
            .join(KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id)
            .where(KnowledgeBinding.collection_id == args.collection)
        )
        revisions = list((await db.scalars(query)).all())

    for revision in sorted(revisions, key=lambda row: row.id):
        if args.revision and revision.id not in args.revision:
            continue
        artifact = (revision.snapshot_metadata or {}).get("qnu_markdown") or {}
        path = artifact.get("structured_path")
        if artifact.get("status") != "ready" or not path:
            print(json.dumps({"revision_id": revision.id, "status": artifact.get("status")}, ensure_ascii=False))
            continue
        stored = QnuStructuredDocument.model_validate_json(await storage_service.get(path))
        reference = stored.document_meta.get("raw_evidence") or {}
        if not reference.get("path"):
            print(json.dumps({"revision_id": revision.id, "skip": "no raw evidence"}, ensure_ascii=False))
            continue
        evidence = json.loads(await storage_service.get(reference["path"]))
        rebuilt = build_pdf_document(evidence, filename=stored.source.filename, sha256=stored.source.sha256)
        markdown = render_qnu_markdown(rebuilt, document_id="ab", revision_id="ab")
        report = validate_qnu_markdown(markdown)
        old, new = profile(stored), profile(rebuilt)
        print(json.dumps({
            "revision_id": revision.id,
            "title": stored.source.filename,
            "validation": {"ok": report.ok, "errors": len(report.errors), "warnings": len(report.warnings)},
            "hash_match": rebuilt.source.sha256 == stored.source.sha256,
            "diff": diff(old, new),
            **({"coverage": coverage(stored, rebuilt)} if args.coverage else {}),
            **({"losing_cells_unpublished": losing_cells(rebuilt, markdown)} if args.cells else {}),
            **({"grep": grep_blocks(rebuilt, args.grep)} if args.grep else {}),
            **({"dump": dump_blocks(rebuilt, stored)} if args.dump else {}),
            **({"conflicts": conflicts(rebuilt)} if args.conflicts else {}),
            **({"rebuilt_profile": new} if args.full else {}),
        }, ensure_ascii=False))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
