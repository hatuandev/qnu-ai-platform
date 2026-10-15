"""Read-only canonical/fact provenance and independent handbook set check; no model calls."""

import argparse
import asyncio
import hashlib
import html
import json
import re
from pathlib import Path

from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine


async def verify(path: Path) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    errors, raw_count, fact_count = [], 0, 0
    async with AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        sources = {}
        for case in report["results"]:
            for citation in case.get("response", {}).get("citations", []):
                source_id = citation["source_revision_id"]
                if source_id not in sources:
                    sources[source_id] = (await db.execute(text(
                        "SELECT canonical_markdown,canonical_hash FROM knowledge_source_revisions WHERE id=:id"),
                        {"id": source_id})).mappings().one()
                source = sources[source_id]
                body = source["canonical_markdown"]
                if citation["canonical_hash"] != source["canonical_hash"] or hashlib.sha256(body.encode("utf-8")).hexdigest() != source["canonical_hash"]:
                    errors.append("source hash mismatch")
                if citation["evidence_origin"] == "canonical":
                    raw_count += 1
                    if body[citation["span_start"]:citation["span_end"]] != citation["quote"]:
                        errors.append("canonical span mismatch")
                else:
                    fact_count += 1
                    fact = (await db.execute(text(
                        "SELECT binding_id,index_revision_id,entity_name,attribute_value FROM knowledge_facts WHERE id=:id"),
                        {"id": citation["fact_id"]})).mappings().one()
                    if (fact["binding_id"] != citation["binding_id"] or fact["index_revision_id"] != citation["index_revision_id"]
                            or fact["entity_name"] not in citation["quote"] or fact["attribute_value"] not in citation["quote"]):
                        errors.append("reviewed fact identity/value mismatch")
        case = next(item for item in report["results"] if item["id"] == "explicit_2025")
        rows = case["response"]["answer_decision"]["records"]
        expected = set()
        # Independent oracle for this diagnostic case, not the runtime record parser.
        for source_id in {source for row in rows for source in row["source_ids"]}:
            for paragraph in re.split(r"(?m)(?=^[ \t]*\d+[.)][ \t]+\*\*)", sources[source_id]["canonical_markdown"]):
                if not re.match(r"\s*\d+[.)]", paragraph):
                    continue
                bold = re.findall(r"\*\*([^*]+)\*\*", paragraph)
                if len(bold) < 2 or not any(all(re.search(term, group, re.IGNORECASE)
                        for term in (r"\btoán\b", r"\blý\b", r"\bhóa\b")) for group in re.findall(r"\([^()]+\)", paragraph)):
                    continue
                expected.add((html.unescape(bold[1]).strip(), html.unescape(bold[0]).strip()))
        actual = {(row["code"], row["name"]) for row in rows}
        if expected != actual:
            errors.append({"missing": sorted(expected - actual), "extra": sorted(actual - expected)})
    print(json.dumps({"raw_citations": raw_count, "reviewed_citations": fact_count,
        "independent_expected": len(expected), "actual": len(actual), "errors": errors,
        "protected_unchanged": report.get("unchanged"), "blocked_destinations": report["blocked_destinations"]}, ensure_ascii=False))
    await engine.dispose()
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    asyncio.run(verify(parser.parse_args().report))
