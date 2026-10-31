"""Offline gold audit against the original PDFs; never consumes model answers."""

import hashlib
import json
import re
from pathlib import Path

import pymupdf


def audit(root: Path) -> dict:
    benchmark = json.loads(
        (root / "frontendV1/e2e/data/admissions-multi-docs.json").read_text(encoding="utf-8")
    )
    pages = {}
    for key, doc in benchmark["documents"].items():
        target = root / doc["path"]
        assert hashlib.sha256(target.read_bytes()).hexdigest() == doc["sha256"], key
        with pymupdf.open(target) as pdf:
            assert len(pdf) == doc["pages"], key
            pages[key] = [page.get_text(sort=True) for page in pdf]
    checked = 0
    for case in benchmark["cases"]:
        for fact in case.get("facts", []):
            texts = [pages[fact["document"]][p - 1] for p in fact["pages"]]
            text = " ".join(texts)
            for value in fact["values"]:
                # Explicit gold numeric kind; preserve decimal vs count semantics.
                tokens = re.findall(r"(?<![\w])\d+(?:[.,]\d+)*(?![\w])", text)
                parsed = []
                for token in tokens:
                    if value["kind"] == "integer" and re.fullmatch(r"\d{1,3}([.,])\d{3}(?:\1\d{3})*", token):
                        token = token.replace(".", "").replace(",", "")
                    else:
                        token = token.replace(",", ".")
                    try:
                        parsed.append(float(token))
                    except ValueError:
                        pass
                assert value["value"] in parsed, (case["id"], fact["document"], fact["pages"], value)
            if "source_row_code" in fact:
                rows = []
                for line in text.splitlines():
                    if fact["source_row_code"] not in line:
                        continue
                    cells = re.findall(r"(?<!\w)(?:\d+(?:[.,]\d+)?|[–—−])(?!\w)", line.split("(")[0])
                    if len(cells) >= 6:
                        rows.append(cells[-4:])
                assert rows, (case["id"], "table row missing", fact["source_row_code"])
                expected = fact["values"][0]["value"]
                assert any(float(row[fact["source_value_column"]].replace(",", ".")) == expected for row in rows), (case["id"], "wrong table column", rows, expected)
            checked += 1
    return {"documents": len(pages), "physical_pages": sum(map(len, pages.values())), "cases": len(benchmark["cases"]), "source_fact_checks": checked, "semantic_review": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(audit(Path(__file__).resolve().parents[1])))
