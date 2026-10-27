"""Verify hashes of legacy files recorded in PORT_BASELINE.sha256."""

from __future__ import annotations

import hashlib
from pathlib import Path

BASELINE = Path("docs/PORT_BASELINE.sha256")
REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    if not BASELINE.exists():
        print("PORT_BASELINE.sha256 chưa có; chưa port tệp nào.")
        return 0
    missing = 0
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, relative = line.split(maxsplit=1)
        target = REPO_ROOT / relative
        if not target.exists():
            print(f"THIẾU {relative}")
            missing += 1
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            print(f"LỆCH {relative}")
            missing += 1
    print("PASS" if missing == 0 else f"FAIL ({missing})")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
