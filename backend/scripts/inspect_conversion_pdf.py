"""Extract native table candidates for human review; never activate rules or update DB."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf


def inspect(source: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Choose a new output; previous evidence is preserved")
    pages = []
    with pymupdf.open(source) as document:
        for page in document:
            tables = []
            for table in page.find_tables().tables:
                rows = table.extract()
                numeric = [index for index, row in enumerate(rows)
                           if row and re.fullmatch(r"\d+(?:[.,]\d+)?%?", (row[0] or "").strip())]
                if not numeric:
                    continue
                depth = numeric[0]
                headers = []
                for column in range(table.col_count):
                    path = []
                    for header in rows[:depth]:
                        label = header[column]
                        if label is None and depth > 1:
                            label = next((header[prior] for prior in range(column - 1, -1, -1) if header[prior]), None)
                        if label and label not in path:
                            path.append(label.replace("\n", " "))
                    headers.append(path)
                tables.append({"bbox": list(table.bbox), "headers": headers, "raw_rows": rows,
                               "data_rows": rows[depth:], "status": "needs_human_review"})
            pages.append({"page": page.number + 1, "text": page.get_text(), "tables": tables})
    result = {"status": "draft_not_active", "origin_file_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
              "source": str(source.resolve()), "pages": pages,
              "warning": "Native extraction only. Validate column geometry, rule, mapping and rounding; do not import as verified automatically."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pages": len(pages), "tables": sum(len(page["tables"]) for page in pages),
                      "status": result["status"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    inspect(arguments.pdf, arguments.output)
