"""Allowlisted, secret-screened validation dossier; never archives Storage or DB."""
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]


def junit(path):
    statuses, causes = {}, {}
    for case in ET.parse(path).getroot().iter("testcase"):
        identity = case.get("classname").replace(".", "/") + ".py::" + case.get("name")
        failed = case.find("failure")
        error = case.find("error")
        status = "ERROR" if error is not None else "FAIL" if failed is not None else "SKIP" if case.find("skipped") is not None else "PASS"
        statuses[identity] = status
        problem = error if error is not None else failed
        if problem is not None:
            causes[identity] = problem.get("message", "").splitlines()[0]
    return {"tests": statuses, "causes": causes, "counts": dict(Counter(statuses.values()))}


def compare(directory):
    after_name = "after-final.xml" if (directory/"after-final.xml").exists() else "after.xml"
    before, after = [junit(directory / name) for name in ("baseline.xml", after_name)]
    common = before["tests"].keys() & after["tests"].keys()
    result = {"baseline": before, "after": after, "after_source": after_name,
        "added_ids": sorted(after["tests"].keys() - before["tests"].keys()),
        "removed_ids": sorted(before["tests"].keys() - after["tests"].keys()),
        "changed": {key: {"before": before["tests"][key], "after": after["tests"][key]} for key in common if before["tests"][key] != after["tests"][key]},
        "new_failing_ids": sorted(key for key, status in after["tests"].items() if status in {"FAIL", "ERROR"} and before["tests"].get(key) not in {"FAIL", "ERROR"}),
        "failure_causes": {key: {"before": before["causes"].get(key), "after": after["causes"].get(key)} for key in before["causes"].keys() | after["causes"].keys()}}
    (directory / "regression-comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def export(directory, destination):
    result = compare(directory)
    # Explicit files only. Model response/corpus, connection configuration and
    # source/object files are deliberately excluded from this evidence archive.
    names = ["baseline.xml", "after.xml", "focused-gate.xml", "patch-isolated.xml", "red.xml", "regression-comparison.json", "commands.json", "live-summary.json", "cleanup.json", "context-metrics-before.json", "context-metrics-after.json"]
    members = {name: (directory / (result["after_source"] if name == "after.xml" else name)).read_bytes() for name in names}
    if result["after_source"] != "after.xml":
        members["after-first.xml"] = (directory / "after.xml").read_bytes()
    for name in ["PATCH_PLAN.md", "IMPLEMENTATION_REPORT.md", "VALIDATION_REPORT.md", "REGRESSION_IDS.md"]:
        members[name] = (ROOT / "docs/bao_cao/context548" / name).read_bytes()
    for name, data in members.items():
        text = data.decode("utf-8")
        if re.search(r"(?i)(bearer\s+[a-z0-9._-]{12,}|sk-[a-z0-9_-]{16,}|postgres(?:ql)?(?:\+\w+)?://[^\s]+|(?:api_key|password|secret_key)\s*[=:]\s*['\"]?[^\s'\"]{8,})", text):
            raise ValueError(f"Possible secret in evidence: {name}; export stopped")
        members[name] = text.replace(str(ROOT), "<repo>").encode("utf-8")
    manifest = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n" for name, data in sorted(members.items()))
    members["manifest.sha256"] = manifest.encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    (destination.parent/"manifest.sha256").write_text(manifest, encoding="utf-8", newline="\n")
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    with ZipFile(destination) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(members)
    zip_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix+".sha256").write_text(zip_hash+"  "+destination.name+"\n", encoding="utf-8", newline="\n")
    print(json.dumps({"zip": str(destination), "sha256": zip_hash,
        "baseline": result["baseline"]["counts"], "after": result["after"]["counts"], "new_failed": result["new_failing_ids"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=ROOT / "backend/storage/context548-evidence")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/bao_cao/context548/evidence.zip")
    args = parser.parse_args()
    export(args.evidence.resolve(), args.output.resolve())
