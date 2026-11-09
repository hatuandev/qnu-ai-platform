"""Fixed local test identities; workspace roles still come from membership in DB.

Only random access-key digests are persisted. This registry is consulted by the
development gate, never SSO, and cannot define arbitrary actors or privileges.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from qnu.domains.identity.actor import AuthActor
from qnu.platform.errors import AppException

ACCOUNTS_PATH = Path(__file__).resolve().parents[3] / ".local" / "dev-accounts.json"
SEED_PROFILES = {
    "ctsv.admin": ("act_dev_ctsv_admin", "Quản trị CTSV (thử nghiệm)", "admin"),
    "ctsv.editor": ("act_dev_ctsv_editor", "Cán bộ CTSV (thử nghiệm)", "editor"),
    "ctsv.user": ("act_dev_ctsv_user", "Người dùng CTSV (thử nghiệm)", "member"),
}
# Pilot identities for the "Trung tâm Số & Học liệu" workspace. Roles are only
# labels here; real privileges still come from the membership row in DB.
SHL_PILOT_PROFILES = {
    "shl.admin": ("act_dev_shl_admin", "Quản trị Trung tâm Số & Học liệu (thử nghiệm)", "admin"),
    "shl.editor": (
        "act_dev_shl_editor",
        "Biên tập viên Trung tâm Số & Học liệu (thử nghiệm)",
        "editor",
    ),
    "shl.reviewer": (
        "act_dev_shl_reviewer",
        "Người duyệt Trung tâm Số & Học liệu (thử nghiệm)",
        "reviewer",
    ),
    "shl.reader": (
        "act_dev_shl_reader",
        "Người tra cứu Trung tâm Số & Học liệu (thử nghiệm)",
        "member",
    ),
}


def resolve_seed_actor(access_key: str) -> AuthActor | None:
    if not ACCOUNTS_PATH.exists():
        return None
    profiles = {**SEED_PROFILES, **SHL_PILOT_PROFILES}
    try:
        digests = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
        if not isinstance(digests, dict) or any(
            name not in profiles
            or not isinstance(value, str)
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            for name, value in digests.items()
        ):
            raise ValueError("Invalid local account registry")
    except (OSError, ValueError) as exc:
        raise AppException(
            "Không đọc được cấu hình tài khoản thử nghiệm local.",
            code="dev_accounts_unavailable",
            status_code=503,
        ) from exc
    candidate = hashlib.sha256(access_key.encode()).hexdigest()
    for name, digest in digests.items():
        if hmac.compare_digest(candidate, digest):
            actor_id, display_name, _ = profiles[name]
            return AuthActor(
                username=name,
                actor_id=actor_id,
                display_name=display_name,
                roles=[],
                permissions=[],
            )
    return None
