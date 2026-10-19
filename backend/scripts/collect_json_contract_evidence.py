"""Metadata-only dossier collector. Run before owned runtime cleanup."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"backend/storage/context549-evidence"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2).replace(str(ROOT), "<repo>")+"\n", encoding="utf-8", newline="\n")


def main():
    state = read(ROOT/"backend/storage/context549-isolation.json")
    runtime = Path(state["runtime"])
    table = read(runtime/"live-table/report.json")
    api = read(runtime/"live-api-verified/report.json")
    summaries, traces = {}, {}
    for key, report, folder in [("table", table, "live-table"), ("api", api, "live-api-verified")]:
        validation = report.get("output_validation") or report.get("context_incomplete") or {}
        model = validation.get("model", {})
        stages = dict(report["stages"])
        correction = None
        if key == "api" and validation.get("stage") == "context_expansion" and model:
            stages.update(provider="PASS", response_complete="PASS" if model.get("finish_reason") == "stop" else "UNKNOWN",
                json_syntax="PASS", selector_schema="PASS", context_expansion="FAIL", evidence_binding="NOT_RUN")
            correction = "Original API report marked pre-expansion stages NOT_RUN. Corrected here from real model/attempt and exception raised after parsing; no new inference."
        metrics = dict(validation.get("metrics", {}))
        metrics["validation_attempt_ms"] = metrics.pop("binding_ms", None)
        summaries[key] = {"status": report["status"], "scope": "selected_tables" if key == "table" else "document",
            "requested_table_ids": ["qnu:t001"] if key == "table" else None, "stages": stages,
            "error_code": report.get("error_code"), "reason": validation.get("reason"), "metrics": metrics,
            "provider_error_class": None, "model": model, "exit_code": report["exit_code"],
            "fixture_sha256": report["fixture_sha256"], "human_approved": False, "source_applied": False,
            "bookkeeping_correction": correction, "attempts": report.get("attempts", []),
            "elapsed_ms": report.get("elapsed_ms"), "api_auth": report.get("api_auth")}
        traces[key] = []
        for path in sorted((runtime/folder).glob("response-*.json")):
            raw = read(path)
            content = raw["content"]
            trace = {name: value for name, value in raw.items() if name != "content"}
            trace["raw_content_sha256"] = hashlib.sha256(content.encode()).hexdigest()
            # Redaction is descriptive only; never fed back into runtime/parser.
            parsed = json.loads(content)
            redacted = {"context_id": parsed.get("context_id"), "top_level_fields": sorted(parsed),
                "list_counts": {name: len(value) for name, value in parsed.items() if isinstance(value, list)}}
            trace["redacted_view"] = redacted
            trace["redacted_view_sha256"] = hashlib.sha256(json.dumps(redacted, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            traces[key].append(trace)
    write(OUT/"live-summary.json", {"old_raw548": "NOT_AVAILABLE", "schema_enforcement": "NOT_VERIFIED",
        "live": summaries, "human_review": "NOT_RUN: no valid proposal", "end_to_end": "BLOCKED"})
    write(OUT/"redacted-live-trace.json", traces)
    write(OUT/"capabilities.json", read(runtime/"capabilities/capabilities.json"))
    paths = subprocess.check_output(["git", "ls-files", "-m", "-o", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    sources = [path for path in paths if path.startswith("backend/") and (ROOT/path).is_file()]
    write(OUT/"commands.json", {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "cwd": "<repo>", "runs": [read(path) for path in sorted(OUT.glob("*-run.json"))],
        "checks": read(OUT/"checks.json"), "source_sha256": {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in sources},
        "baseline_source_sha256": read(OUT/"baseline-code-hashes.json"), "fixture_sha256": table["fixture_sha256"],
        "baseline": "baseline-configured.xml (same test DB configuration; frozen app code)",
        "unconfigured_baseline": "baseline.xml; extra MODEL_DEFAULT_NOT_CONFIGURED was a setup difference"})
    print(json.dumps({"source_files": len(sources), "live_table": summaries["table"]["error_code"], "live_api": summaries["api"]["error_code"]}))


if __name__ == "__main__": main()
