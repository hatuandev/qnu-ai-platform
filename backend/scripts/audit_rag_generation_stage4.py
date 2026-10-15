"""Two real stage-four chats; no OCR, source/index/config mutations or fake outputs.

Uses the stage-one observation wrappers unchanged; conversation IDs retain their
legacy prefix. --live creates ordinary chat/usage/key-health records. Artifacts
are local diagnostic data, not fixtures fed to the model. No correctness score
is inferred merely from status or numeric substring overlap.
"""

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.core.database import engine
from scripts.audit_rag_floor_stage1 import CASES, fingerprint, inspect_publication, trace_case


class BudgetObservation(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.events.append(record.getMessage())


async def run(output: Path, live: bool) -> None:
    if output.exists():
        raise ValueError("Choose a new output path; preserving earlier diagnostic")
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("configuration_fingerprint", "snapshot_fingerprint", "target_data_fingerprint",
              "collection_metadata_fingerprint", "inventory")
    before = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
    report = {"phase": 4, "started_at": datetime.now(UTC).isoformat(),
              "live": live, "before": {key: fingerprint(before[key]) for key in fields}, "results": []}
    observer = BudgetObservation()
    logger = logging.getLogger("app.modules.modelops.providers.context_budget")
    level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(observer)
    try:
        if live:
            for case in CASES:
                current = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
                if any(report["before"][key] != fingerprint(current[key]) for key in fields):
                    raise ValueError("Publication/config changed; stopping")
                result = await asyncio.wait_for(trace_case(case, "admissions"), timeout=180)
                report["results"].append(result)
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({"case": case["id"], "elapsed_ms": result["elapsed_ms"],
                                  "status": result.get("response", {}).get("status"),
                                  "error": result.get("error_code")}), flush=True)
    finally:
        logger.removeHandler(observer)
        logger.setLevel(level)
        report["context_events"] = observer.events
        after = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
        report["unchanged"] = {key: report["before"][key] == fingerprint(after[key]) for key in fields}
        report["finished_at"] = datetime.now(UTC).isoformat()
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("storage/rag_stage4_469/report.json"))
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.output, args.live))
