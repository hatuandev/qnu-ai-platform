"""Export the OpenAPI document for contract review."""

from __future__ import annotations

import json
from pathlib import Path

from qnu.main import app


def main() -> int:
    output = Path("docs/openapi-v1.json")
    output.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
