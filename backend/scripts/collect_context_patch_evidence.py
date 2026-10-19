"""Collect metadata only; no credentials, model text, DB dump or object archive."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend/storage/context548-evidence"
state = json.loads((ROOT/"backend/storage/context548-isolation.json").read_text(encoding="utf-8"))
paths = subprocess.run(["git", "diff", "--name-only"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
paths += [str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT/"backend/scripts").glob("*context_patch*")]
paths += ["backend/app/modules/knowledge/services/semantic_context_review.py", "backend/app/modules/knowledge/services/semantic_run_budget.py", "backend/tests/test_context548_patch.py"]
paths = sorted({p for p in paths if p.startswith(("backend/", "frontend/")) and (ROOT/p).is_file()})
commands = {"cwd": "<repo>", "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
    "runs": [json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT.glob("*-run.json"))],
    "source_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
    "baseline_source_sha256": json.loads((OUT/"baseline-code-hashes.json").read_text(encoding="utf-8")),
    "fixture_sha256": hashlib.sha256((ROOT/"docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx").read_bytes()).hexdigest(),
    "recorded_checks": json.loads((OUT/"checks.json").read_text(encoding="utf-8")),
    "scope": "test database with owned nonce, temporary local Storage; no production migrations"}
(OUT/"commands.json").write_text(json.dumps(commands, ensure_ascii=False, indent=2).replace(str(ROOT), "<repo>")+"\n", encoding="utf-8", newline="\n")
live_path = Path(state["runtime"])/"live"
live = json.loads((live_path/"report.json").read_text(encoding="utf-8"))
response = live_path/"response-1.json"
summary = {"attempts": 1, "scope": {"kind": "selected_tables", "table_ids": ["qnu:t001"]},
    "status": live["status"], "provider_inference": live.get("provider_inference", "NOT_RUN"),
    "error_code": live.get("error_code"), "output_validation": live.get("output_validation"),
    "stages": {"provider": live.get("provider_inference", "NOT_RUN"), "selector_schema": "FAIL" if live.get("error_code") == "SEMANTIC_OUTPUT_INVALID" else "NOT_RUN",
        "evidence_binding": "NOT_RUN", "proposal": "FAIL", "human_review": "NOT_RUN", "apply": "NOT_RUN", "persist_reload": "NOT_RUN"},
    "failures": live.get("failures", []), "exit_code": live["exit_code"], "human_approved": False, "source_applied": False,
    "fixture_sha256": live["fixture_sha256"], "request_scope_complete": True,
    "response_sha256": hashlib.sha256(response.read_bytes()).hexdigest() if response.exists() else None,
    "provider_error_class": None if live.get("provider_inference") == "PASS" else live.get("failure_category"),
    "timings_ms": {"build": live.get("output_validation", {}).get("metrics", {}).get("build_ms"),
        "model": live.get("output_validation", {}).get("metrics", {}).get("model_ms"),
        "schema_validation_attempt": live.get("output_validation", {}).get("metrics", {}).get("binding_ms"),
        "evidence_binding": None},
    "notes": "Original report retained. Selector/schema and binding statuses here separate parsing failure from nonexistent evidence validation."}
if response.exists():
    content = json.loads(response.read_text(encoding="utf-8"))["content"]
    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        summary["json_error"] = {"type": type(exc).__name__, "reason": exc.msg, "line": exc.lineno, "column": exc.colno}
(OUT/"live-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")
print(json.dumps({"source_files": len(paths), "run_reports": len(commands["runs"]), "live": summary["error_code"]}))
