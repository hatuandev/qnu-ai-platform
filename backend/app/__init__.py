"""QNU.AI Platform Backend Application Package."""

from __future__ import annotations

import os

# Sanitize no_proxy on Windows: httpx crashes when parsing IPv6 addresses like '::1' and '::1/128'
for _env_var in ("no_proxy", "NO_PROXY"):
    _val = os.environ.get(_env_var)
    if _val:
        _cleaned = [item.strip() for item in _val.split(",") if not item.strip().startswith("::")]
        os.environ[_env_var] = ",".join(_cleaned)

__version__ = "0.1.0"
