"""Idempotent SHL pilot workspace members and local dev access keys.

Run from backendV1: uv run --frozen --env-file ../.env python -m scripts.seed_shl_pilot
Uses the workspace services for authorization and audit. Never renames the
workspace, changes existing roles/status, resets credentials or creates corpus.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import sys

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from qnu.domains.identity.dev_accounts import ACCOUNTS_PATH, SHL_PILOT_PROFILES
from qnu.domains.identity.dev_gate import dev_gate_enabled, issue_dev_token
from qnu.domains.workspaces.models import Workspace, WorkspaceMember
from qnu.domains.workspaces.schemas import MemberCreateRequest, WorkspaceCreateRequest
from qnu.domains.workspaces.service import workspace_service
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory, engine

WORKSPACE_CODE = "shl"
WORKSPACE_NAME = "Trung tâm Số & Học liệu"
WORKSPACE_DESCRIPTION = "Không gian thử nghiệm nghiệp vụ của Trung tâm Số & Học liệu."
CREDENTIALS_PATH = ACCOUNTS_PATH.with_name("shl-pilot-accounts.json")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def ensure_local_environment() -> None:
    settings = get_settings()
    if not dev_gate_enabled() or make_url(settings.DATABASE_URL).host not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise RuntimeError("Seed chỉ dành cho dev gate và PostgreSQL local.")


async def seed_workspace() -> dict[str, object]:
    ensure_local_environment()
    _, admin = issue_dev_token(get_settings().DEV_ACCESS_PASSWORD)
    created: list[str] = []
    members: list[dict[str, str]] = []
    async with AsyncSessionFactory() as db, engine.connect() as lock:
        await lock.execute(text("SELECT pg_advisory_lock(20261028, 699)"))
        try:
            workspace = await db.scalar(select(Workspace).where(Workspace.code == WORKSPACE_CODE))
            if workspace is None:
                workspace = await workspace_service.create_workspace(
                    db,
                    WorkspaceCreateRequest(
                        code=WORKSPACE_CODE,
                        name=WORKSPACE_NAME,
                        description=WORKSPACE_DESCRIPTION,
                    ),
                    admin,
                )
                created.append("workspace")
            if workspace.status != "active":
                raise RuntimeError("Workspace hiện có đang tạm dừng; seed không tự kích hoạt lại.")
            for name, (actor_id, display_name, role) in SHL_PILOT_PROFILES.items():
                member = await db.scalar(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace.id,
                        WorkspaceMember.actor_ref == actor_id,
                    )
                )
                if member is None:
                    member = await workspace_service.add_member(
                        db,
                        workspace.id,
                        MemberCreateRequest(
                            actor_ref=actor_id,
                            display_name=display_name,
                            role=role,
                        ),
                        admin,
                    )
                    created.append(name)
                elif member.role != role or member.status != "active":
                    raise RuntimeError(f"Membership {name} đã thay đổi; seed không ghi đè.")
                members.append({"profile": name, "actor_ref": actor_id, "role": member.role})
            return {
                "workspace_id": workspace.id,
                "code": workspace.code,
                "name": workspace.name,
                "created": created,
                "members": members,
            }
        finally:
            await lock.execute(text("SELECT pg_advisory_unlock(20261028, 699)"))
            await db.rollback()


def ensure_credentials() -> None:
    ACCOUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry: dict[str, str] = {}
    if ACCOUNTS_PATH.exists():
        registry = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
        if not isinstance(registry, dict):
            raise RuntimeError("Sổ tài khoản local không hợp lệ; seed không tự sửa.")

    if CREDENTIALS_PATH.exists():
        credentials = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        if set(credentials) != set(SHL_PILOT_PROFILES):
            raise RuntimeError("Tệp khóa SHL không khớp danh tính; seed không tự thay khóa.")
        expected = {
            name: hashlib.sha256(key.encode()).hexdigest() for name, key in credentials.items()
        }
        if any(registry.get(name) != digest for name, digest in expected.items()):
            raise RuntimeError("Sổ tài khoản local không khớp khóa SHL; seed không tự thay khóa.")
        return

    if any(name in registry for name in SHL_PILOT_PROFILES):
        raise RuntimeError(
            "Sổ tài khoản đã có danh tính SHL nhưng thiếu tệp khóa; không tự thay khóa."
        )

    credentials = {name: secrets.token_urlsafe(32) for name in SHL_PILOT_PROFILES}
    digests = {name: hashlib.sha256(key.encode()).hexdigest() for name, key in credentials.items()}
    with CREDENTIALS_PATH.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(credentials, ensure_ascii=False, indent=2) + "\n")
    merged = {**registry, **digests}
    temporary = ACCOUNTS_PATH.with_name(ACCOUNTS_PATH.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, ACCOUNTS_PATH)
    except OSError:
        CREDENTIALS_PATH.unlink(missing_ok=True)
        raise


async def main() -> None:
    ensure_local_environment()
    try:
        result = await seed_workspace()
        ensure_credentials()
        print(json.dumps(result, ensure_ascii=False))
        print(f"Khóa đăng nhập local được lưu riêng tại: {CREDENTIALS_PATH}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
