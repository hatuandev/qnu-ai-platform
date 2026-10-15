"""Read-only publication + fact audit for the score-conversion table (session 482 Task A).

No model/OCR calls, no reindex, no publication change, no writes.
"""

import asyncio
import json
import re
import unicodedata
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.database import AsyncSessionFactory
from app.modules.rag.retriever import hybrid_retriever

TARGET_FILE = "Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed.pdf"
EXPECTED = {
    "binding_id": "bnd_e52fd3712ac3",
    "source_revision_id": "ks_rev_259de8772948",
    "index_revision_id": "idx_rev_5f5f3f114ca1",
    "canonical_hash": "ddceee8b1442a36cb3359e2ce9f54850646384a3086be87c25e25a2c8bc9fd2f",
    "origin_file_hash": "96207cca90ecd30df23d9ffcf74fb982a6277e4d89b08270e3465a4a2bd5dc8e",
    "chunk_count": 116,
    "fact_count": 534,
    "source_revision_no": 3,
}
OUTPUT = Path("backend/storage/rag_conversion_482/audit_a.json")


def nfc(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def serializable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, dict):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


async def main() -> None:
    report: dict[str, Any] = {"mode": "read_only_audit", "writes": 0, "model_calls": 0}
    async with AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))

        collection = dict((await db.execute(text(
            "SELECT id, name, tenant_id, workspace_id, is_active, index_epoch, collection_metadata "
            "FROM knowledge_collections WHERE id='col_admissions'"))).mappings().one())
        meta = collection.pop("collection_metadata") or {}
        report["collection"] = collection
        report["collection_metadata_keys"] = sorted(meta.keys())
        report["has_score_conversion_rules"] = "score_conversion_rules" in meta

        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
            db, "col_admissions", tenant_id=collection["tenant_id"], workspace_id=collection["workspace_id"])
        report["snapshot"] = snapshot.model_dump()

        rows = [dict(r) for r in (await db.execute(text("""
            SELECT b.id AS binding_id, b.status AS binding_status,
                   i.id AS index_id, i.status AS index_status,
                   i.source_revision_v2_id, i.chunk_count, i.fact_count, i.parity_report,
                   s.id AS source_id, s.revision_no, s.status AS source_status,
                   s.canonical_hash, s.origin_file_hash, s.snapshot_metadata, s.citation_metadata,
                   s.parse_provenance, s.canonical_markdown
            FROM knowledge_bindings b
            LEFT JOIN knowledge_index_revisions i ON i.id = b.active_index_revision_id
            LEFT JOIN knowledge_source_revisions s ON s.id = i.source_revision_v2_id
            WHERE b.collection_id = :col ORDER BY b.id
        """), {"col": "col_admissions"})).mappings()]

        inventory = []
        target = None
        for row in rows:
            entry = {k: row.get(k) for k in (
                "binding_id", "binding_status", "index_id", "index_status", "source_id",
                "revision_no", "source_status", "canonical_hash", "origin_file_hash",
                "chunk_count", "fact_count")}
            file_name = (row.get("snapshot_metadata") or {}).get("file_name")
            entry["file_name"] = file_name
            entry["in_snapshot"] = snapshot.binding_revisions.get(row["binding_id"]) == row["index_id"]
            inventory.append(entry)
            if file_name == TARGET_FILE:
                target = row
        report["binding_inventory"] = inventory
        report["target_found"] = target is not None

        if target is None:
            report["error"] = "target publication not found"
            _save(report)
            return

        report["reference_check"] = {
            key: {"expected": expected, "actual": serializable(target.get(db_key, target.get(key))),
                  "match": serializable(target.get(db_key, target.get(key))) == expected}
            for key, expected, db_key in [
                ("binding_id", EXPECTED["binding_id"], "binding_id"),
                ("source_revision_id", EXPECTED["source_revision_id"], "source_id"),
                ("index_revision_id", EXPECTED["index_revision_id"], "index_id"),
                ("canonical_hash", EXPECTED["canonical_hash"], "canonical_hash"),
                ("origin_file_hash", EXPECTED["origin_file_hash"], "origin_file_hash"),
                ("source_revision_no", EXPECTED["source_revision_no"], "revision_no"),
                ("chunk_count", EXPECTED["chunk_count"], "chunk_count"),
                ("fact_count", EXPECTED["fact_count"], "fact_count"),
            ]}
        report["statuses"] = {k: target.get(k) for k in (
            "binding_status", "index_status", "source_status")}
        report["parity_report"] = serializable(target.get("parity_report"))
        report["citation_metadata"] = serializable(target.get("citation_metadata"))
        provenance = target.get("parse_provenance") or {}
        report["parse_provenance_keys"] = sorted(provenance.keys())
        report["layout_version"] = provenance.get("layout_version") or provenance.get("artifact_version")
        report["snapshot_file_metadata"] = serializable({
            k: v for k, v in (target.get("snapshot_metadata") or {}).items() if k != "page_manifest"})

        live_chunks = (await db.execute(text(
            "SELECT COUNT(*) FROM knowledge_chunks WHERE index_revision_id=:i"),
            {"i": target["index_id"]})).scalar_one()
        live_facts = (await db.execute(text(
            "SELECT COUNT(*) FROM knowledge_facts WHERE index_revision_id=:i"),
            {"i": target["index_id"]})).scalar_one()
        report["live_counts"] = {"chunks": live_chunks, "facts": live_facts}

        facts = [dict(r) for r in (await db.execute(text(
            "SELECT id, entity_name, entity_key, entity_label, entity_type, entity_code, "
            "attribute_name, attribute_value, attribute_code, applicability_year, raw_data, binding_id "
            "FROM knowledge_facts WHERE index_revision_id=:i ORDER BY id"),
            {"i": target["index_id"]})).mappings()]

        canonical = nfc(target.get("canonical_markdown") or "")
        report["canonical_length"] = len(canonical)
        formula_hits = {}
        for label, pattern in {
            "interpolation": r"nội\s*suy",
            "percentile": r"bách\s*phân\s*vị|phần\s*trăm|top\s*%",
            "rounding": r"làm\s*tròn",
            "two_decimals": r"hai\s*chữ\s*số\s*thập\s*phân|0?[,\.]?\d*\s*chữ\s*số\s*thập\s*phân",
            "adjacent_marks": r"liền\s*kề",
            "base_combination": r"tổ\s*hợp\s*gốc",
            "year_2026": r"\b2026\b",
            "year_2025": r"\b2025\b",
            "applies": r"áp\s*dụng",
        }.items():
            matches = re.findall(pattern, canonical, re.IGNORECASE)
            formula_hits[label] = len(matches)
        report["canonical_formula_evidence"] = formula_hits
        rounding_ctx = []
        for m in re.finditer(r"làm\s*tròn", canonical, re.IGNORECASE):
            start = max(0, m.start() - 120)
            rounding_ctx.append(canonical[start:m.end() + 120])
        report["rounding_context_quotes"] = rounding_ctx[:6]
        year_ctx = []
        for m in list(re.finditer(r"(?:áp\s*dụng|năm\s+tuyển\s*sinh|tuyển\s*sinh)[^.]{0,80}", canonical, re.IGNORECASE))[:10]:
            year_ctx.append(m.group(0))
        report["year_context_quotes"] = year_ctx

        tables: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "rows": defaultdict(list), "attributes": Counter(), "entity_names": Counter(),
            "pages": Counter(), "years": Counter(), "cells": []})
        for fact in facts:
            raw = fact.get("raw_data") or {}
            table_id = raw.get("table_id")
            row_index = raw.get("row_index")
            col_index = raw.get("column_index")
            page = raw.get("page_number") or (fact.get("citation_metadata") or {}).get("page_number")
            key = table_id if table_id is not None else "no_table"
            entry = tables[key]
            entry["rows"][row_index].append(fact)
            entry["attributes"][nfc(fact["attribute_name"])] += 1
            entry["entity_names"][nfc(fact["entity_name"])] += 1
            entry["pages"][page] += 1
            temporal = raw.get("temporal_context") or {}
            year = fact.get("applicability_year") or temporal.get("year")
            entry["years"][str(year)] += 1
            entry["cells"].append({
                "fact_id": fact["id"], "table_id": table_id, "row_index": row_index,
                "column_index": col_index, "page": page,
                "entity_name": nfc(fact["entity_name"]), "entity_code": fact.get("entity_code"),
                "entity_type": fact.get("entity_type"),
                "attribute": nfc(fact["attribute_name"]), "value": nfc(fact["attribute_value"]),
                "attribute_code": fact.get("attribute_code"), "year": year,
                "temporal_status": temporal.get("status") or ("set" if year else "unknown"),
                "has_cell_bbox": bool(raw.get("cell_bbox") or raw.get("bbox") or raw.get("native_bbox")),
                "raw_keys": sorted(raw.keys()),
            })

        report["tables"] = {}
        for table_id, entry in tables.items():
            cells = entry["cells"]
            col_indexes = sorted({c["column_index"] for c in cells if c["column_index"] is not None})
            report["tables"][str(table_id)] = {
                "fact_count": len(cells),
                "row_count": len(entry["rows"]),
                "row_indexes": sorted(k for k in entry["rows"] if k is not None)[:40],
                "distinct_attributes": len(entry["attributes"]),
                "attributes": dict(entry["attributes"].most_common(40)),
                "distinct_entity_names": len(entry["entity_names"]),
                "entity_name_samples": dict(entry["entity_names"].most_common(60)),
                "pages": dict(entry["pages"]),
                "column_indexes": col_indexes[:40],
                "distinct_column_count": len(col_indexes),
                "years": dict(entry["years"]),
                "cells_with_bbox": sum(1 for c in cells if c["has_cell_bbox"]),
                "sample_cells": cells[:8],
                "raw_key_union": sorted({k for c in cells for k in c["raw_keys"]}),
            }

        # Oracle: locate DNL 764/790 rows and the A01-group THPT column values.
        report["oracle"] = {"found_pairs": []}
        dnl_values: dict[str, dict[str, Any]] = {}
        for fact in facts:
            raw = fact.get("raw_data") or {}
            attr = nfc(fact["attribute_name"])
            val = nfc(fact["attribute_value"])
            if re.fullmatch(r"(?i)\s*đnl\s*|đánh\s*gía\s*năng\s*lực.*", attr) or attr.upper() == "ĐNL":
                dnl_values.setdefault(str(raw.get("row_index")), {"row": raw.get("row_index"),
                    "table": raw.get("table_id"), "page": raw.get("page_number"),
                    "dnl_fact": fact["id"], "dnl_value": val, "siblings": {}})
            entry = dnl_values.get(str(raw.get("row_index")))
            if entry and entry.get("table") == raw.get("table_id"):
                entry["siblings"][attr] = {"fact_id": fact["id"], "value": val,
                    "column_index": raw.get("column_index")}
        for want_x1, want_x2 in [("764", "790")]:
            by_value: dict[str, list[dict]] = defaultdict(list)
            for entry in dnl_values.values():
                by_value[entry["dnl_value"]].append(entry)
            rows_x1 = by_value.get(want_x1, [])
            rows_x2 = by_value.get(want_x2, [])
            for r1 in rows_x1:
                for r2 in rows_x2:
                    if r1["table"] != r2["table"]:
                        continue
                    common_attrs = [a for a in r1["siblings"] if a in r2["siblings"]
                                    and a not in ("ĐNL",)]
                    for attr in common_attrs:
                        try:
                            y1 = Decimal(r1["siblings"][attr]["value"].replace(",", "."))
                            y2 = Decimal(r2["siblings"][attr]["value"].replace(",", "."))
                        except InvalidOperation:
                            continue  # A non-numeric column is a label, not an oracle pair.
                        x1, x2 = Decimal(want_x1), Decimal(want_x2)
                        score = Decimal(780)
                        y = (y1 + (score - x1) * (y2 - y1) / (x2 - x1)).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP)
                        report["oracle"]["found_pairs"].append({
                            "table": r1["table"], "row_x1": r1["row"], "row_x2": r2["row"],
                            "attribute": attr, "x1": str(x1), "y1": str(y1),
                            "x2": str(x2), "y2": str(y2), "input": "780",
                            "interpolated_half_up": str(y),
                            "facts": [r1["dnl_fact"], r2["dnl_fact"],
                                      r1["siblings"][attr]["fact_id"], r2["siblings"][attr]["fact_id"]],
                            "pages": [r1.get("page"), r2.get("page")],
                        })

        # Mapping appendix: entity_name shapes for combination rows.
        combo_shape = Counter()
        combo_samples: list[dict] = []
        for fact in facts:
            entity = nfc(fact["entity_name"])
            value = nfc(fact["attribute_value"])
            attr = nfc(fact["attribute_name"])
            if re.fullmatch(r"[A-D][0-9]{2}", entity) or re.fullmatch(r"[A-D][0-9]{2}", value) \
               or re.search(r"tổ\s*hợp", attr, re.IGNORECASE):
                shape = ("code_entity" if re.fullmatch(r"[A-D][0-9]{2}", entity) else "non_code_entity")
                combo_shape[shape] += 1
                if len(combo_samples) < 40:
                    combo_samples.append({"fact_id": fact["id"], "entity_name": entity,
                        "attribute": attr, "value": value,
                        "table": (fact.get("raw_data") or {}).get("table_id"),
                        "row": (fact.get("raw_data") or {}).get("row_index"),
                        "page": (fact.get("raw_data") or {}).get("page_number")})
        report["combination_mapping_shape"] = dict(combo_shape)
        report["combination_mapping_samples"] = combo_samples

        unknown_year = sum(1 for f in facts
                           if not (f.get("applicability_year") or (f.get("raw_data") or {}).get("temporal_context", {}).get("year")))
        report["facts_without_year"] = unknown_year
        report["fact_year_distribution"] = dict(Counter(
            str(f.get("applicability_year") or (f.get("raw_data") or {}).get("temporal_context", {}).get("year") or "unknown")
            for f in facts))

    _save(report)


def _save(report: dict[str, Any]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(serializable(report), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {OUTPUT.resolve()}")
    summary_keys = ("has_score_conversion_rules", "reference_check", "statuses", "live_counts",
                    "canonical_formula_evidence", "facts_without_year", "combination_mapping_shape")
    for key in summary_keys:
        print(f"{key}: {json.dumps(report.get(key), ensure_ascii=False)[:600]}")


if __name__ == "__main__":
    asyncio.run(main())
