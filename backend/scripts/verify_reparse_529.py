"""Read-only cross-check of each reparse-derived revision against the revision it came from.

Verifies the stored MD/JSON pair (identity + checksum), provenance equality, and that every
numeric token of the base canonical text still appears in the derived one. Writes nothing.
"""

import argparse
import asyncio
import json
import re
from collections import Counter

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.services.qnu_serving import verify_revision_pair
from app.modules.knowledge.services.source_artifact import get_source_artifact

_NUMERIC = re.compile(r"\d+(?:[.,]\d+)*")


def _counts(markdown: str) -> Counter[str]:
    return Counter(_NUMERIC.findall(markdown or ""))


def _states(document) -> Counter[str]:
    states: Counter[str] = Counter()
    for block in document.blocks:
        fields = block.attributes.get("fields")
        if isinstance(fields, dict):
            for value in fields.values():
                if isinstance(value, dict):
                    states[str(value.get("state"))] += 1
    return states


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--pair", action="append", default=[], help="base_id:new_id")
    args = parser.parse_args()

    async with AsyncSessionFactory() as db:
        if args.pair:
            pairs = [tuple(item.split(":")) for item in args.pair]
        else:
            rows = list(
                (
                    await db.scalars(
                        select(KnowledgeSourceRevision)
                        .join(KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id)
                        .where(
                            KnowledgeBinding.collection_id == args.collection,
                            KnowledgeSourceRevision.revision_no > 1,
                        )
                    )
                ).all()
            )
            pairs = []
            for revision in sorted(rows, key=lambda row: (row.binding_id, row.revision_no)):
                base = await db.scalar(
                    select(KnowledgeSourceRevision).where(
                        KnowledgeSourceRevision.binding_id == revision.binding_id,
                        KnowledgeSourceRevision.revision_no == revision.revision_no - 1,
                    )
                )
                if base:
                    pairs.append((base.id, revision.id))

        for base_id, new_id in pairs:
            base = await db.get(KnowledgeSourceRevision, base_id)
            new = await db.get(KnowledgeSourceRevision, new_id)
            result = {
                "binding_id": new.binding_id,
                "base_revision_id": base.id,
                "revision_id": new.id,
                "revision_no": new.revision_no,
                "status": new.status,
                "provenance_same_snapshot": new.snapshot_storage_path == base.snapshot_storage_path,
                "provenance_same_hash": new.origin_file_hash == base.origin_file_hash,
                "parser_profile": (new.parse_provenance or {}).get("parser_profile"),
                "engine_used": (new.parse_provenance or {}).get("ocr_engine"),
            }
            try:
                document = await verify_revision_pair(new)
                result["pair_valid"] = True
            except Exception as error:
                result["pair_valid"] = False
                result["pair_error"] = getattr(error, "code", type(error).__name__)
                print(json.dumps(result, ensure_ascii=True), flush=True)
                continue
            standard = (new.snapshot_metadata or {}).get("qnu_markdown") or {}
            old_counts, new_counts = _counts(base.canonical_markdown), _counts(new.canonical_markdown)
            result.update(
                {
                    "standard_status": standard.get("status"),
                    "canonical_format": (new.parse_provenance or {}).get("canonical_format"),
                    "blocks": document.stats.get("block_count")
                    if isinstance(document.stats, dict)
                    else len(document.blocks),
                    "figures": sum(1 for block in document.blocks if block.type == "figure"),
                    "field_states": dict(_states(document)),
                    "base_field_states": dict(_states(await verify_revision_pair(base))),
                    "numeric_tokens_base": sum(old_counts.values()),
                    "numeric_tokens_new": sum(new_counts.values()),
                    "numeric_tokens_lost": {
                        token: count - new_counts.get(token, 0)
                        for token, count in old_counts.items()
                        if count > new_counts.get(token, 0)
                    },
                    "numeric_tokens_added": {
                        token: count - old_counts.get(token, 0)
                        for token, count in new_counts.items()
                        if count > old_counts.get(token, 0)
                    },
                    "unresolved_cells": get_source_artifact(new).get("unresolved_cell_count", 0),
                    "issue_codes": sorted(
                        {
                            issue.get("code", "unknown")
                            for issue in get_source_artifact(new).get("issues", [])
                        }
                    ),
                }
            )
            print(json.dumps(result, ensure_ascii=True), flush=True)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
