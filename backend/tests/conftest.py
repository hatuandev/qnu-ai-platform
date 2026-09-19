"""Pytest configuration and environment sanitization for QNU AI Platform tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path when running pytest from workspace root
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Sanitize no_proxy on Windows: httpx crashes on IPv6 addresses like '::1' and '::1/128'
for env_var in ("no_proxy", "NO_PROXY"):
    val = os.environ.get(env_var)
    if val:
        cleaned = [item.strip() for item in val.split(",") if not item.strip().startswith("::")]
        os.environ[env_var] = ",".join(cleaned)

# Enforce local storage driver for unit tests to prevent network dependencies on offline MinIO
os.environ["STORAGE_DRIVER"] = "local"
os.environ["ENVIRONMENT"] = "test"

from app.core.config import get_settings

get_settings.cache_clear()

