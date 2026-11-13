"""Run a pytest selection in parallel shards, each against its own disposable database.

Pilot for the full backend gate: the same tests and assertions, split by file using a
previous junit report for balancing, executed as independent ``test_database.py`` runs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "storage" / "context636"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def resolve_module_file(classname: str) -> str | None:
    parts = [part for part in classname.split(".") if part]
    while parts:
        candidate = ROOT.joinpath(*parts).with_suffix(".py")
        if candidate.is_file():
            return candidate.relative_to(ROOT).as_posix()
        parts.pop()
    return None


def file_weights(reports: list[Path]) -> dict[str, float]:
    """Sum the worst observed duration of each test id per file, so partial or
    repeated baseline runs do not double-count and chunks can be merged."""
    merged: dict[tuple[str, str, str], float] = {}
    for report in reports:
        for case in ET.parse(report).getroot().iter("testcase"):
            module = resolve_module_file(case.get("classname") or "")
            if module is None:
                continue
            key = (module, case.get("classname") or "", case.get("name") or "")
            seconds = float(case.get("time") or 0)
            merged[key] = max(merged.get(key, 0.0), seconds)
    weights: dict[str, float] = {}
    for (module, _, _), seconds in merged.items():
        weights[module] = weights.get(module, 0.0) + seconds
    return weights


def discover_files(selections: list[str]) -> list[str]:
    found: set[str] = set()
    for raw in selections or ["tests"]:
        target = raw.split("::", 1)[0]
        path = ROOT / target
        if path.is_file() and path.suffix == ".py":
            found.add(path.relative_to(ROOT).as_posix())
        elif path.is_dir():
            for file in path.rglob("test_*.py"):
                found.add(file.relative_to(ROOT).as_posix())
        else:
            raise SystemExit(f"Unknown test path: {raw}")
    if not found:
        raise SystemExit("No test files discovered for the given selection.")
    return sorted(found)


def split_evenly(files: list[str], durations: dict[str, float], shards: int) -> list[list[str]]:
    known = [durations[file] for file in files if file in durations]
    fallback = statistics.median(known) if known else 30.0
    ordered = sorted(files, key=lambda file: (-durations.get(file, fallback), file))
    buckets: list[list[str]] = [[] for _ in range(shards)]
    loads = [0.0] * shards
    for file in ordered:
        index = min(range(shards), key=lambda position: (loads[position], position))
        buckets[index].append(file)
        loads[index] += durations.get(file, fallback)
    return buckets


def receipt_from_log(path: Path) -> dict | None:
    if not path.is_file():
        return None
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        if line.startswith('{"database"'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return None
    return None


def case_outcomes(xml_path: Path) -> dict[str, str]:
    outcomes: dict[str, str] = {}
    for case in ET.parse(xml_path).getroot().iter("testcase"):
        key = (case.get("classname") or "") + "::" + (case.get("name") or "")
        if case.find("failure") is not None:
            outcomes[key] = "failed"
        elif case.find("error") is not None:
            outcomes[key] = "error"
        elif case.find("skipped") is not None:
            outcomes[key] = "skipped"
        else:
            outcomes[key] = "passed"
    return outcomes


def run_wave(buckets: list[list[str]], flags: list[str], runtime: Path, offset: int) -> list[dict]:
    wave: list[dict] = []
    for index, bucket in enumerate(buckets, start=offset + 1):
        log_path = runtime / f"shard-{index}.log"
        command = [sys.executable, str(ROOT / "scripts" / "test_database.py"), *bucket, *flags]
        stream = log_path.open("w", encoding="utf-8")
        started = time.monotonic()
        # Settings resolve .env from the process CWD; the canonical env file lives at repo root.
        process = subprocess.Popen(
            command, cwd=ROOT.parent, stdout=stream, stderr=subprocess.STDOUT
        )
        wave.append(
            {
                "index": index,
                "files": bucket,
                "process": process,
                "stream": stream,
                "log": log_path,
                "started": started,
            }
        )
    for shard in wave:
        shard["process"].wait()
        shard["stream"].close()
        shard["wall_seconds"] = round(time.monotonic() - shard["started"], 2)
        shard["exit"] = shard["process"].returncode
    return wave


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=0)
    parser.add_argument("--balance-from", type=Path, nargs="+", default=None)
    parser.add_argument("--label", default="")
    known, passthrough = parser.parse_known_args()
    if known.shards < 2:
        parser.error("--shards must be at least 2")

    selections: list[str] = []
    flags: list[str] = []
    for argument in passthrough:
        if argument.startswith("-"):
            flags.append(argument)
        elif (ROOT / argument.split("::", 1)[0]).exists():
            selections.append(argument)
        else:
            flags.append(argument)

    files = discover_files(selections)
    for report in known.balance_from or []:
        if not report.is_file():
            raise SystemExit(f"Baseline report not found: {report}")
    durations = file_weights(known.balance_from) if known.balance_from else {}
    shards = min(known.shards, len(files))
    jobs = min(known.jobs or shards, shards)

    runtime = RUNTIME_ROOT / ("sharded_" + uuid.uuid4().hex[:8])
    runtime.mkdir(parents=True)
    buckets = split_evenly(files, durations, shards)
    (runtime / "plan.json").write_text(
        json.dumps(
            {
                "label": known.label,
                "shards": shards,
                "jobs": jobs,
                "balance_from": [str(report) for report in known.balance_from or []],
                "files": len(files),
                "buckets": buckets,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"plan: {len(files)} files, ~{sum(durations.values()) / 60:.1f} min baseline, "
        f"{shards} shards, {jobs} jobs -> {runtime}"
    )

    started = time.monotonic()
    queue = list(buckets)
    results: list[dict] = []
    while queue:
        wave, queue = queue[:jobs], queue[jobs:]
        results.extend(run_wave(wave, flags, runtime, len(results)))

    outcomes: dict[str, str] = {}
    duplicates: list[str] = []
    shard_summaries: list[dict] = []
    for shard in results:
        receipt = receipt_from_log(shard["log"])
        database = (receipt or {}).get("database", "")
        xml_path = RUNTIME_ROOT / database / "result.xml" if database else None
        cases = case_outcomes(xml_path) if xml_path and xml_path.is_file() else {}
        for key in cases:
            if key in outcomes:
                duplicates.append(key)
        outcomes.update(cases)
        shard_summaries.append(
            {
                "index": shard["index"],
                "exit": shard["exit"],
                "wall_seconds": shard["wall_seconds"],
                "database": database,
                "files": len(shard["files"]),
                "tests": len(cases),
                "failed": sorted(k for k, v in cases.items() if v == "failed"),
                "errors": sorted(k for k, v in cases.items() if v == "error"),
                "skipped": len([v for v in cases.values() if v == "skipped"]),
            }
        )

    comparison: dict[str, list[str]] = {}
    if known.balance_from:
        baseline: dict[str, str] = {}
        for report in known.balance_from:
            baseline.update(case_outcomes(report))
        comparison = {
            "missing_vs_baseline": sorted(set(baseline) - set(outcomes)),
            "new_vs_baseline": sorted(set(outcomes) - set(baseline)),
            "failure_diff_vs_baseline": sorted(
                key
                for key, value in outcomes.items()
                if value in {"failed", "error"} and baseline.get(key) not in {"failed", "error"}
            ),
        }
        comparison["fixed_vs_baseline"] = sorted(
            key
            for key, value in baseline.items()
            if value in {"failed", "error"} and outcomes.get(key) == "passed"
        )

    summary = {
        "label": known.label,
        "wall_seconds": round(time.monotonic() - started, 2),
        "tests": len(outcomes),
        "failures": sorted(k for k, v in outcomes.items() if v in {"failed", "error"}),
        "duplicates": sorted(set(duplicates)),
        "shards": shard_summaries,
        "comparison": comparison,
    }
    (runtime / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for shard in shard_summaries:
        print(
            f"shard {shard['index']}: exit {shard['exit']}, {shard['tests']} tests, "
            f"{shard['wall_seconds']:.0f}s, failed {len(shard['failed'])}, "
            f"errors {len(shard['errors'])}"
        )
    selected_baseline = sum(durations.get(file, 0.0) for file in files)
    print(
        f"summary: {summary['tests']} tests, {len(summary['failures'])} failed/error, "
        f"wall {summary['wall_seconds']:.0f}s, "
        f"selected baseline {selected_baseline:.0f}s"
    )
    if comparison:
        print(
            "vs baseline: "
            f"missing {len(comparison['missing_vs_baseline'])}, "
            f"new {len(comparison['new_vs_baseline'])}, "
            f"new failures {len(comparison['failure_diff_vs_baseline'])}, "
            f"fixed {len(comparison['fixed_vs_baseline'])}"
        )
    for key in summary["failures"]:
        print(f"FAILED {key}")
    for key in summary["duplicates"]:
        print(f"DUPLICATE {key}")

    ok = all(shard["exit"] == 0 for shard in results) and not duplicates
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
