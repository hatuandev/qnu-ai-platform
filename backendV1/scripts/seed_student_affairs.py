"""Idempotent local CTSV workspace + development accounts, without sample corpus.

Run from backendV1: uv run --frozen --env-file ../.env python -m scripts.seed_student_affairs
Uses the existing workspace services for authorization and audit. Never changes
existing roles/status, resets credentials, migrates schema or grants models.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from qnu.domains.identity.dev_accounts import ACCOUNTS_PATH, SEED_PROFILES
from qnu.domains.identity.dev_gate import dev_gate_enabled, issue_dev_token
from qnu.domains.knowledge.collections.schemas import CollectionCreateRequest
from qnu.domains.knowledge.collections.service import collection_service
from qnu.domains.knowledge.models import KBCollection
from qnu.domains.workspaces.models import Workspace, WorkspaceMember
from qnu.domains.workspaces.schemas import MemberCreateRequest, WorkspaceCreateRequest
from qnu.domains.workspaces.service import workspace_service
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory, engine

WORKSPACE_CODE = "cong-tac-sinh-vien"
COLLECTION_NAME = "Tri thức Công tác sinh viên (thử nghiệm)"
CREDENTIALS_PATH = ACCOUNTS_PATH.with_name("ctsv-test-accounts.json")


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
    created = []
    # Serialize repeated invocations across service commits.
    async with AsyncSessionFactory() as db, engine.connect() as lock:
        await lock.execute(text("SELECT pg_advisory_lock(20261028, 698)"))
        try:
            workspace = await db.scalar(select(Workspace).where(Workspace.code == WORKSPACE_CODE))
            if workspace is None:
                workspace = await workspace_service.create_workspace(
                    db,
                    WorkspaceCreateRequest(
                        code=WORKSPACE_CODE,
                        name="Phòng Công tác sinh viên",
                        description="Workspace thử nghiệm phân quyền của Phòng Công tác sinh viên.",
                    ),
                    admin,
                )
                created.append("workspace")
            if workspace.status != "active":
                raise RuntimeError("Workspace hiện có đang tạm dừng; seed không tự kích hoạt lại.")
            for name, (actor_id, display_name, role) in SEED_PROFILES.items():
                member = await db.scalar(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace.id,
                        WorkspaceMember.actor_ref == actor_id,
                    )
                )
                if member is None:
                    await workspace_service.add_member(
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
            collection = await db.scalar(
                select(KBCollection).where(
                    KBCollection.workspace_id == workspace.id,
                    KBCollection.name == COLLECTION_NAME,
                )
            )
            if collection is None:
                collection = await collection_service.create(
                    db,
                    workspace,
                    CollectionCreateRequest(
                        name=COLLECTION_NAME,
                        description="Kho trống để thử upload tài liệu của đơn vị.",
                    ),
                    admin,
                )
                created.append("collection")
            return {
                "workspace_id": workspace.id,
                "collection_id": collection.id,
                "created": created,
            }
        finally:
            await lock.execute(text("SELECT pg_advisory_unlock(20261028, 698)"))


def ensure_credentials() -> None:
    ACCOUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ACCOUNTS_PATH.exists() or CREDENTIALS_PATH.exists():
        credentials = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        expected = {
            name: hashlib.sha256(credentials[name].encode()).hexdigest() for name in SEED_PROFILES
        }
        if json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8")) != expected:
            raise RuntimeError("Tệp tài khoản local không khớp; seed không tự thay khóa.")
        return
    credentials = {name: secrets.token_urlsafe(32) for name in SEED_PROFILES}
    digests = {name: hashlib.sha256(key.encode()).hexdigest() for name, key in credentials.items()}
    # Exclusive creation avoids silently replacing existing credentials.
    with CREDENTIALS_PATH.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(credentials, ensure_ascii=False, indent=2) + "\n")
    with ACCOUNTS_PATH.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(digests, indent=2) + "\n")


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
