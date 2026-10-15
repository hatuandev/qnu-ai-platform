"""Dry-run acceptance for the score-conversion tool against the live publication.

Read-only: the draft rules are injected into a proxy session, never written to the database.
Everything else (snapshot resolution, published blocks, reviewed fact rows, matching, engine
arithmetic, RFC 7807 errors) is the real production path. No model call is made.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.rag.score_conversion import convert_admission_score
from app.modules.rag.score_conversion_schemas import ScoreConversionRequest

RULES_FILE = Path("storage/rag_conversion_482/conversion_rules.json")
OUTPUT = Path("storage/rag_conversion_482/acceptance_dry_run.json")
COLLECTION = "col_admissions"

# (name, request overrides, expected status, expected result/reason)
CASES: list[tuple[str, dict, str, str]] = [
    ("published_oracle_A01_780", {"combination": "A01", "score": "780"}, "calculated", "21.21"),
    ("half_up_midpoint_A01_777", {"combination": "A01", "score": "777"}, "calculated", "21.13"),
    ("exact_mark_A01_790", {"combination": "A01", "score": "790"}, "calculated", "21.50"),
    ("exact_mark_A01_764", {"combination": "A01", "score": "764"}, "calculated", "20.75"),
    ("top_mark_A01", {"combination": "A01", "score": "1024"}, "calculated", None),
    ("bottom_mark_A01", {"combination": "A01", "score": "27"}, "calculated", None),
    ("decimal_comma_A01", {"combination": "A01", "score": "780,5"}, "calculated", None),
    ("mapped_code_X26_equals_base_A01", {"combination": "X26", "score": "780"}, "calculated", "21.21"),
    ("mapped_code_A02_uses_base_A00", {"combination": "A02", "score": "780"}, "calculated", None),
    ("outside_range_below", {"combination": "A01", "score": "26"}, "missing", "SCORE_OUTSIDE_VERIFIED_RANGE"),
    ("outside_range_above", {"combination": "A01", "score": "1025"}, "missing", "SCORE_OUTSIDE_VERIFIED_RANGE"),
    ("wrong_year_2025", {"combination": "A01", "score": "780", "year": 2025}, "missing", "NO_VERIFIED_CONVERSION_RULE"),
    ("spt_exam_has_no_rule", {"combination": "A01", "score": "780", "source_method": "SPT"}, "missing", "NO_VERIFIED_CONVERSION_RULE"),
    ("thpt_as_source_has_no_rule", {"combination": "A01", "score": "21", "source_method": "THPT"}, "missing", "NO_VERIFIED_CONVERSION_RULE"),
    ("hb_as_source_has_no_rule", {"combination": "A01", "score": "21", "source_method": "HB"}, "missing", "NO_VERIFIED_CONVERSION_RULE"),
    ("unlisted_combination_A03", {"combination": "A03", "score": "780"}, "missing", "NO_VERIFIED_CONVERSION_RULE"),
    ("foreign_combination_ZZ99", {"combination": "ZZ99", "score": "780"}, "missing", "NO_VERIFIED_CONVERSION_RULE"),
    ("base_B00", {"combination": "B00", "score": "900"}, "calculated", None),
    ("base_C00", {"combination": "C00", "score": "900"}, "calculated", None),
    ("base_C01", {"combination": "C01", "score": "900"}, "calculated", None),
    ("base_D01", {"combination": "D01", "score": "900"}, "calculated", None),
    ("base_D07", {"combination": "D07", "score": "900"}, "calculated", None),
    ("alias_dgnl", {"combination": "A01", "score": "780", "source_method": "ĐGNL"}, "calculated", "21.21"),
    ("alias_full_name", {"combination": "A01", "score": "780", "source_method": "đánh giá năng lực"}, "calculated", "21.21"),
]


class RuleOverlay:
    """Forwards every real column, but serves the draft rules instead of the persisted metadata."""

    def __init__(self, row, rules: list[dict]) -> None:
        self._row = row
        self.collection_metadata = {**(row.collection_metadata or {}), "score_conversion_rules": rules}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._row, name)


class OutageSession:
    """Every read fails, the way a dropped connection does."""

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError("DB down")

    async def get(self, model, ident, **kwargs):
        raise RuntimeError("DB down")


class DryRunSession:
    """Real session, but the collection carries the draft rules instead of persisted ones."""

    def __init__(self, session, rules: list[dict]) -> None:
        self._session = session
        self._rules = rules

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    async def get(self, model, ident, **kwargs):
        row = await self._session.get(model, ident, **kwargs)
        if model is KnowledgeCollection and row is not None:
            return RuleOverlay(row, self._rules)
        return row


async def main() -> None:
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    report: dict[str, Any] = {"mode": "dry_run_read_only", "writes": 0, "model_calls": 0,
                              "rules": len(rules), "cases": [], "failures": []}
    async with AsyncSessionFactory() as session:
        await session.execute(text("SET TRANSACTION READ ONLY"))
        collection = await session.get(KnowledgeCollection, COLLECTION)
        tenant_id, workspace_id = collection.tenant_id, collection.workspace_id
        db = DryRunSession(session, rules)
        for name, over, expected_status, expected_value in CASES:
            payload = {"collection_id": COLLECTION, "year": 2026, "source_method": "ĐNL",
                       "combination": "A01", "score": "780", **over}
            entry: dict[str, Any] = {"case": name, "request": payload}
            try:
                result = await convert_admission_score(db, ScoreConversionRequest.model_validate(payload),
                                                       tenant_id=tenant_id, workspace_id=workspace_id)
                entry.update({"status": result.status, "reason": result.reason, "result": result.result,
                              "bracket": [result.x1, result.y1, result.x2, result.y2],
                              "target_attribute": None, "citations": len(result.citations),
                              "evidence_blocks": len(result.evidence_block_ids)})
                observed = result.result if result.status == "calculated" else result.reason
                ok = result.status == expected_status and (expected_value is None or observed == expected_value)
            except AppException as exc:
                entry.update({"status": "error", "reason": exc.code})
                ok = expected_status == "error" and expected_value == exc.code
            entry["passed"] = ok
            report["cases"].append(entry)
            if not ok:
                report["failures"].append(f"{name}: expected {expected_status}/{expected_value}, got {entry}")
        # A database outage must surface as an error, never as a fabricated answer.
        try:
            await convert_admission_score(OutageSession(), ScoreConversionRequest.model_validate(
                {"collection_id": COLLECTION, "year": 2026, "source_method": "ĐNL",
                 "combination": "A01", "score": "780"}), tenant_id=tenant_id, workspace_id=workspace_id)
            report["failures"].append("db_outage: expected AppException, got an answer")
        except AppException as exc:
            entry = {"case": "db_outage_is_not_an_answer", "status": "error", "reason": exc.code,
                     "passed": exc.code == "SCORE_RULE_UNAVAILABLE"}
            report["cases"].append(entry)
            if not entry["passed"]:
                report["failures"].append(f"db_outage: expected SCORE_RULE_UNAVAILABLE, got {exc.code}")
        # A foreign tenant must be refused before any rule is read: no answer, and no leak that
        # the collection exists (the retriever answers 404 rather than 403 by design).
        try:
            await convert_admission_score(db, ScoreConversionRequest.model_validate(
                {"collection_id": COLLECTION, "year": 2026, "source_method": "ĐNL",
                 "combination": "A01", "score": "780"}), tenant_id="tenant_other", workspace_id=workspace_id)
            report["failures"].append("foreign_tenant: expected refusal, got an answer")
        except AppException as exc:
            entry = {"case": "foreign_tenant_refused", "status": "error", "reason": exc.code,
                     "status_code": exc.status_code, "passed": exc.status_code in (403, 404)}
            report["cases"].append(entry)
            if not entry["passed"]:
                report["failures"].append(f"foreign_tenant: expected 403/404, got {exc.status_code}/{exc.code}")

    report["passed"] = not report["failures"]
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "rules": report["rules"], "cases": len(report["cases"]),
                      "passed": report["passed"], "failures": report["failures"],
                      "summary": [{c["case"]: c.get("result") or c.get("reason")} for c in report["cases"]]},
                     ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
