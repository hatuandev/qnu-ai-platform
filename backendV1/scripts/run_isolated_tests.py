"""Run backendV1 tests against an isolated database URL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.test_database import main

if __name__ == "__main__":
    raise SystemExit(main())
