"""Test bootstrap: deterministic environment and an isolated database."""

from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("STORAGE_DRIVER", "local")
os.environ.setdefault("DEV_AUTH_ENABLED", "true")
os.environ.setdefault("DEV_ACCESS_PASSWORD", "test-pass")
os.environ.setdefault("PROVIDER_ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("SECRET_KEY", "test-only-signing-key-at-least-32-bytes-long")

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()

if TEST_DATABASE_URL:
    import re

    from sqlalchemy.engine import make_url

    test_url = make_url(TEST_DATABASE_URL)
    if not re.fullmatch(r"qnu_v1_test_[a-z0-9_]+", test_url.database or ""):
        raise RuntimeError("TEST_DATABASE_URL phải trỏ database sở hữu riêng qnu_v1_test_* .")
    # The application engine reads DATABASE_URL at import time; point it at the test DB.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
