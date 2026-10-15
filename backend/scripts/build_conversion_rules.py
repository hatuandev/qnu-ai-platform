"""Derive reviewed score-conversion rules from the publication that is serving right now.

Read-only unless both --activate and --reviewed-by are supplied. No mark, combination list,
fact id or answer is typed here: every value is read from the live index revision, and each
generated rule is re-verified through the production engine before it is emitted.
"""

import argparse
import asyncio
import json
import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from itertools import pairwise
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest
from app.modules.rag.score_conversion import calculate_verified_score
from app.modules.rag.score_conversion_schemas import (
    CombinationMapping,
    ConversionPoint,
    ConversionRule,
    ScoreConversionRequest,
    SourceCell,
    parse_score,
)

# Reference publication for this session. Resolved again at runtime; a mismatch stops the run
# so stale ids can never be used to configure the tool.
REFERENCE = {
    "binding_id": "bnd_e52fd3712ac3",
    "source_revision_id": "ks_rev_259de8772948",
    "index_revision_id": "idx_rev_5f5f3f114ca1",
    "canonical_hash": "ddceee8b1442a36cb3359e2ce9f54850646384a3086be87c25e25a2c8bc9fd2f",
    "origin_file_hash": "96207cca90ecd30df23d9ffcf74fb982a6277e4d89b08270e3465a4a2bd5dc8e",
    "source_revision_no": 3,
}
OUTPUT_DIR = Path("storage/rag_conversion_482")


class Abort(RuntimeError):
    """A gate failed; nothing may be configured."""


def nfc(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def tokens(label: str) -> list[str]:
    return [part for part in re.split(r"\W+", unicodedata.normalize("NFC", label)) if part]


def quantize(value: Decimal, places: int, rounding: str) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 40
        return value.quantize(Decimal(1).scaleb(-places), rounding=rounding)


async def resolve_publication(db, policy: dict) -> tuple[Any, dict]:
    snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, policy["collection_id"])
    rows = [dict(r) for r in (await db.execute(text(
        "SELECT b.id AS binding_id, b.status AS binding_status, i.id AS index_id, i.status AS index_status, "
        "i.chunk_count, i.fact_count, s.id AS source_id, s.revision_no, s.status AS source_status, "
        "s.canonical_hash, s.origin_file_hash, s.snapshot_metadata "
        "FROM knowledge_bindings b "
        "LEFT JOIN knowledge_index_revisions i ON i.id = b.active_index_revision_id "
        "LEFT JOIN knowledge_source_revisions s ON s.id = i.source_revision_v2_id "
        "WHERE b.collection_id = :col"), {"col": policy["collection_id"]})).mappings()]
    target = next((r for r in rows if (r.get("snapshot_metadata") or {}).get("file_name") == policy["target_file"]), None)
    if target is None:
        raise Abort(f"Nguồn '{policy['target_file']}' không có trong bộ sưu tập")
    if (target["binding_status"], target["index_status"], target["source_status"]) != ("active", "active", "ready"):
        raise Abort(f"Nguồn chưa phục vụ: {target['binding_status']}/{target['index_status']}/{target['source_status']}")
    if snapshot.binding_revisions.get(target["binding_id"]) != target["index_id"]:
        raise Abort("Snapshot hiện hành không trỏ vào index revision của nguồn này")
    actual = {"binding_id": target["binding_id"], "source_revision_id": target["source_id"],
              "index_revision_id": target["index_id"], "canonical_hash": target["canonical_hash"],
              "origin_file_hash": target["origin_file_hash"], "source_revision_no": target["revision_no"]}
    if actual != REFERENCE:
        raise Abort(f"Publication đã thay đổi so với tham chiếu; dừng cấu hình: {actual}")
    return snapshot, target


async def row_order(db, index_revision_id: str) -> dict[str, tuple[str, int]]:
    rows = await db.execute(text(
        "SELECT id, raw_data->>'table_id' AS table_id, (raw_data->>'row_index')::int AS row_index "
        "FROM knowledge_facts WHERE index_revision_id = :i"), {"i": index_revision_id})
    return {row[0]: (row[1], row[2]) for row in rows if row[1] is not None and row[2] is not None}


def proof_quote(blocks: list[EvidenceBlock], anchor: str) -> tuple[str, str]:
    wanted = nfc(anchor)
    hits = [b for b in blocks if b.origin == "canonical" and wanted in nfc(b.text)]
    if len(hits) != 1:
        raise Abort(f"Neo bằng chứng '{anchor}' khớp {len(hits)} khối canonical, cần đúng 1")
    if len(hits[0].text) > 4000:
        raise Abort(f"Khối bằng chứng cho '{anchor}' dài hơn giới hạn trích dẫn")
    return hits[0].id, hits[0].text


def cell_of(block: EvidenceBlock, attribute: str) -> dict:
    matches = [c for c in block.fact_context.get("cells", []) if c["attribute"] == attribute]
    if len(matches) != 1:
        raise Abort(f"Hàng {block.fact_context.get('entity_name')} có {len(matches)} ô '{attribute}', cần đúng 1")
    return matches[0]


def derive_rules(policy: dict, grid: list[EvidenceBlock], mapping: list[EvidenceBlock],
                 proofs: list[dict], identity: dict) -> list[ConversionRule]:
    source_attribute = policy["source_attribute"]
    base_labels = {c["attribute"] for b in mapping for c in b.fact_context.get("cells", [])}
    if len(base_labels) != 1:
        raise Abort(f"Hàng ánh xạ phải có đúng một nhãn tổ hợp gốc, nhận được {sorted(base_labels)}")
    base_label = base_labels.pop()
    code_labels = {entry[0] for b in mapping for entry in (b.fact_context.get("row_context") or [])}
    if len(code_labels) != 1:
        raise Abort(f"Hàng ánh xạ phải có đúng một nhãn mã tổ hợp, nhận được {sorted(code_labels)}")
    code_label = code_labels.pop()
    for block in mapping:
        entries = block.fact_context.get("row_context") or []
        if len(entries) != 1 or entries[0][0] != code_label:
            raise Abort(f"Hàng '{block.fact_context.get('entity_name')}' không đơn trị về mã tổ hợp")
    codes = [block.fact_context["row_context"][0][1] for block in mapping]
    if len(set(codes)) != len(codes):
        raise Abort("Mã tổ hợp trùng lặp; không tự chọn hàng")

    bases = sorted({cell_of(b, base_label)["value"] for b in mapping})
    columns = sorted({c["attribute"] for b in grid for c in b.fact_context["cells"]} - {source_attribute})
    target_of = {}
    for base in bases:
        candidates = [c for c in columns if tokens(c)[:1] == [base] and policy["target_method"] in tokens(c)[1:]]
        if len(candidates) != 1:
            raise Abort(f"Không xác định được duy nhất cột đích cho tổ hợp gốc {base}: {candidates}")
        target_of[base] = candidates[0]

    rules = []
    for base in bases:
        target_attribute = target_of[base]
        points = []
        for block in grid:
            source = cell_of(block, source_attribute)
            target = cell_of(block, target_attribute)
            points.append(ConversionPoint(
                source=SourceCell(block_id=block.id, fact_id=source["fact_id"],
                                  attribute=source["attribute"], value=source["value"]),
                target=SourceCell(block_id=block.id, fact_id=target["fact_id"],
                                  attribute=target["attribute"], value=target["value"])))
        mappings = [CombinationMapping(combination=block.fact_context["row_context"][0][1], base_combination=base,
            proof=SourceCell(block_id=block.id, fact_id=cell_of(block, base_label)["fact_id"],
                             attribute=base_label, value=base))
            for block in mapping if cell_of(block, base_label)["value"] == base]
        if not mappings:
            raise Abort(f"Không có ánh xạ nào cho tổ hợp gốc {base}")
        rules.append(ConversionRule(id=f"qnu-{policy['year']}-{source_attribute}-{base}-{policy['target_method']}",
            status="verified", reviewed_by=identity["reviewed_by"], reviewed_at=identity["reviewed_at"],
            binding_id=identity["binding_id"], index_revision_id=identity["index_revision_id"],
            source_revision_id=identity["source_revision_id"], canonical_hash=identity["canonical_hash"],
            year=policy["year"], source_method=policy["source_method"], source_attribute=source_attribute,
            source_aliases=policy.get("source_aliases", []), target_method=policy["target_method"],
            target_attribute=target_attribute, base_combination=base,
            combination_context_attribute=code_label, mappings=mappings, points=points,
            operation="piecewise_linear", decimal_places=policy["decimal_places"], rounding=policy["rounding"],
            rule_proofs=proofs))
    return rules


def independent_value(x1: Decimal, y1: Decimal, x2: Decimal, y2: Decimal, score: Decimal,
                      places: int, rounding: str) -> Decimal:
    """Second implementation of the reviewed formula, used only to cross-check the engine."""
    if x1 <= score <= x2:
        return quantize(y1 + (score - x1) * (y2 - y1) / (x2 - x1), places, rounding)
    if x2 <= score <= x1:
        return quantize(y2 + (score - x2) * (y1 - y2) / (x1 - x2), places, rounding)
    raise Abort(f"Điểm {score} ngoài khoảng mốc {x1}..{x2}")


def verify_rule(rule: ConversionRule, index: dict[str, EvidenceBlock], snapshot, policy: dict) -> dict:
    report: dict[str, Any] = {"rule_id": rule.id, "base": rule.base_combination,
                              "target_attribute": rule.target_attribute, "mappings": len(rule.mappings),
                              "points": len(rule.points), "checks": 0, "failures": []}

    def request_for(combination: str, score: str, **over) -> ScoreConversionRequest:
        return ScoreConversionRequest.model_validate({"collection_id": policy["collection_id"],
            "year": rule.year, "source_method": rule.source_method, "combination": combination,
            "score": score, **over})

    def record(name: str, ok: bool, detail: str = "") -> None:
        report["checks"] += 1
        if not ok:
            report["failures"].append(f"{name}: {detail}")

    marks = sorted({(parse_score(p.source.value), parse_score(p.target.value)) for p in rule.points})
    brackets = list(pairwise(marks))
    probes = {(x1 + x2) / 2 for (x1, _), (x2, _) in brackets}
    probes |= {x1 + (x2 - x1) / Decimal(4) for (x1, _), (x2, _) in brackets}
    probes = {p for p in probes if p == p.quantize(Decimal("0.01"))}

    for position, mapping in enumerate(rule.mappings):
        sweep = marks if position == 0 else (marks[0], marks[len(marks) // 2], marks[-1])
        for source, target in sweep:
            result = calculate_verified_score(request_for(mapping.combination, str(source)), rule, index, snapshot)
            expected = quantize(target, rule.decimal_places, rule.rounding)
            record(f"mark[{mapping.combination}]={source}", result.status == "calculated"
                   and Decimal(result.result) == expected, f"{result.result} != {expected}")
        if position:
            continue
        for (x1, y1), (x2, y2) in brackets:
            for probe in sorted(p for p in probes if x1 < p < x2):
                result = calculate_verified_score(request_for(mapping.combination, str(probe)), rule, index, snapshot)
                expected = independent_value(x1, y1, x2, y2, probe, rule.decimal_places, rule.rounding)
                record(f"interior={probe}", result.status == "calculated"
                       and Decimal(result.result) == expected, f"{result.result} != {expected}")

    low, high = marks[0][0], marks[-1][0]
    for outside in (low - 1, high + 1):
        result = calculate_verified_score(request_for(rule.mappings[0].combination, str(outside)), rule, index, snapshot)
        record(f"outside={outside}", result.status == "missing" and result.result is None, result.status)

    for name, mutate in [
        ("tampered_cell", lambda r, i: i[r.points[0].target.block_id].fact_context["cells"][0].update(value="0.01")),
        ("stale_index", lambda r, i: setattr(r, "index_revision_id", "idx_rev_superseded")),
        ("foreign_source", lambda r, i: setattr(i[r.points[0].source.block_id], "source_revision_id", "ks_rev_other")),
        ("wrong_year", None), ("wrong_method", None), ("unknown_combination", None),
    ]:
        clone = rule.model_copy(deep=True)
        clone_index = {b.id: b.model_copy(deep=True) for b in index.values()}
        payload = request_for(rule.mappings[0].combination, str(marks[0][0]))
        if name == "wrong_year":
            payload = payload.model_copy(update={"year": rule.year - 1})
        elif name == "wrong_method":
            payload = payload.model_copy(update={"source_method": "kỳ thi khác"})
        elif name == "unknown_combination":
            payload = payload.model_copy(update={"combination": "ZZ99"})
        else:
            mutate(clone, clone_index)
        try:
            outcome = calculate_verified_score(payload, clone, clone_index, snapshot)
            rejected, detail = outcome.status != "calculated", outcome.status
        except ValueError as exc:
            rejected, detail = True, str(exc)
        record(f"reject_{name}", rejected, detail)

    oracle = policy.get("oracle")
    if oracle and oracle["combination"] in {m.combination for m in rule.mappings}:
        result = calculate_verified_score(request_for(oracle["combination"], oracle["score"]), rule, index, snapshot)
        record("published_oracle", result.status == "calculated" and result.result == oracle["expected"]
               and (result.x1, result.y1, result.x2, result.y2) == (oracle["x1"], oracle["y1"], oracle["x2"], oracle["y2"]),
               f"{result.x1}/{result.y1}/{result.x2}/{result.y2} -> {result.result}")
    report["passed"] = not report["failures"]
    return report


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=OUTPUT_DIR / "reviewed_policy.json")
    parser.add_argument("--activate", action="store_true",
                        help="Ghi rule vào collection_metadata; mặc định chỉ sinh bản nháp read-only")
    parser.add_argument("--reviewed-by", default=None,
                        help="Danh tính người có quyền quản trị đã duyệt cấu hình công cụ")
    args = parser.parse_args()

    if args.activate and not args.reviewed_by:
        raise SystemExit("--activate bắt buộc phải có --reviewed-by là danh tính người duyệt thật")
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"generated_at": datetime.now(UTC).isoformat(), "mode": "activate" if args.activate else "draft",
                              "policy": {k: v for k, v in policy.items() if not k.startswith("_")}, "writes": 0}

    async with AsyncSessionFactory() as db:
        if not args.activate:
            await db.execute(text("SET TRANSACTION READ ONLY"))
        snapshot, target = await resolve_publication(db, policy)
        report["publication"] = {"binding_id": target["binding_id"], "index_revision_id": target["index_id"],
                                 "source_revision_id": target["source_id"], "revision_no": target["revision_no"],
                                 "canonical_hash": target["canonical_hash"], "chunk_count": target["chunk_count"],
                                 "fact_count": target["fact_count"], "snapshot_id": snapshot.snapshot_id,
                                 "tenant_id": snapshot.tenant_id, "workspace_id": snapshot.workspace_id}
        pinned = snapshot.model_copy(update={"binding_revisions": {target["binding_id"]: target["index_id"]}})
        blocks = await load_published_blocks(db, pinned)
        req = AskRequest(question="Score conversion", collection_id=policy["collection_id"],
                         tenant_id=snapshot.tenant_id, workspace_id=snapshot.workspace_id)
        rows = await reviewed_fact_blocks(db, req, pinned, QueryPlan(query=req.question), blocks, exhaustive=True)
        order = await row_order(db, target["index_id"])

        grid = [b for b in rows if any(c["attribute"] == policy["source_attribute"] for c in b.fact_context.get("cells", []))]
        grid_ids = {b.id for b in grid}
        mapping = [b for b in rows if b.id not in grid_ids and b.fact_context.get("row_context")]
        report["evidence"] = {"published_blocks": len(blocks), "fact_blocks": len(rows),
                              "grid_rows": len(grid), "mapping_rows": len(mapping),
                              "unclassified": len(rows) - len(grid) - len(mapping)}
        if not grid or not mapping or report["evidence"]["unclassified"]:
            raise Abort(f"Không phân loại dứt khoát được bằng chứng: {report['evidence']}")
        if any(b.fact_id not in order for b in (*grid, *mapping)):
            raise Abort("Một số hàng bằng chứng thiếu row_index đã duyệt trong nguồn")
        tables = {order[b.fact_id][0] for b in grid}
        if len(tables) != 1 or None in tables:
            raise Abort(f"Hàng bách phân vị phải thuộc đúng một bảng, nhận được {tables}")
        grid.sort(key=lambda b: order[b.fact_id][1])  # Preserve the reviewed row order; never sort by value.
        mapping.sort(key=lambda b: order[b.fact_id][1])

        resolved = {name: proof_quote(blocks, anchor) for name, anchor in policy["proof_anchors"].items()}
        proofs = [{"block_id": block_id, "quote": quote} for block_id, quote in resolved.values()]
        report["rule_proofs"] = [{"anchor": name, "block_id": block_id} for name, (block_id, _) in resolved.items()]
        identity = {"reviewed_by": args.reviewed_by or "pending-operator-review", "reviewed_at": datetime.now(UTC),
                    "binding_id": target["binding_id"], "index_revision_id": target["index_id"],
                    "source_revision_id": target["source_id"], "canonical_hash": target["canonical_hash"]}
        rules = derive_rules(policy, grid, mapping, proofs, identity)
        report["rules"] = [{"id": r.id, "base": r.base_combination, "target_attribute": r.target_attribute,
                            "mappings": [m.combination for m in r.mappings], "points": len(r.points)} for r in rules]

        index = {b.id: b for b in (*blocks, *rows)}  # Canonical proofs and reviewed rows together, as at runtime.
        verifications = [verify_rule(rule, index, pinned, policy) for rule in rules]
        report["verification"] = [{"rule_id": v["rule_id"], "base": v["base"], "points": v["points"],
                                   "mappings": v["mappings"], "checks": v["checks"],
                                   "passed": v["passed"], "failures": v["failures"]} for v in verifications]
        if not all(v["passed"] for v in verifications):
            (OUTPUT_DIR / "verification_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            raise Abort("Một hoặc nhiều rule không vượt qua kiểm chứng; không cấu hình")

        payload = [rule.model_dump(mode="json") for rule in rules]
        (OUTPUT_DIR / "conversion_rules.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.activate:
            collection = await db.get(KnowledgeCollection, policy["collection_id"])
            if collection is None or (collection.tenant_id, collection.workspace_id) != (snapshot.tenant_id, snapshot.workspace_id):
                raise Abort("Không có quyền ghi cấu hình cho bộ sưu tập này")
            merged = dict(collection.collection_metadata or {})
            merged["score_conversion_rules"] = payload
            collection.collection_metadata = merged
            await db.commit()
            report["writes"] = 1
            report["metadata_keys_after"] = sorted(merged)
        else:
            report["activation"] = {
                "status": "not_activated",
                "reason": "reviewed_by chưa được người có quyền quản trị xác nhận",
                "command": ("python -m scripts.build_conversion_rules --activate "
                            '--reviewed-by "<danh tính người duyệt>"'),
            }
        (OUTPUT_DIR / "verification_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    summary = {k: report[k] for k in ("mode", "writes", "evidence", "rules") if k in report}
    summary["verification"] = [{"rule_id": v["rule_id"], "checks": v["checks"], "passed": v["passed"]}
                               for v in report["verification"]]
    summary["activation"] = report.get("activation", {"status": "activated", "rules": len(payload)})
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Abort as exc:
        raise SystemExit(f"DỪNG: {exc}") from exc
