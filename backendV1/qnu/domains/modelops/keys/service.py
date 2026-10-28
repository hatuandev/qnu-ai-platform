"""Credential lifecycle: encrypted storage, masked reads and audited revocation."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.keys.scope import credential_owner, key_scope
from qnu.domains.modelops.models import Provider, ProviderKey, ProviderKeyAudit
from qnu.domains.modelops.schemas import KeyCreateRequest, KeyRotateRequest
from qnu.domains.workspaces.access import actor_ref
from qnu.platform.crypto import encrypt
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.platform.redaction import redact


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def mask_secret(secret: str) -> str:
    """Last four characters only; enough to recognise a key, useless to reuse it."""
    cleaned = secret.strip()
    if len(cleaned) <= 4:
        return "****"
    return f"****{cleaned[-4:]}"


class KeyService:
    async def add_key(
        self,
        db: AsyncSession,
        provider: Provider,
        req: KeyCreateRequest,
        actor: AuthActor,
    ) -> ProviderKey:
        require_model_admin(actor)
        owner = await credential_owner(db, provider.id, lock=True)
        key = ProviderKey(
            id=_new_id("key"),
            provider_id=owner.id,
            model_ids=[provider.id] if provider.parent_id else None,
            name=req.name,
            secret_encrypted=encrypt(req.secret),
            masked_hint=mask_secret(req.secret),
            status="active",
            priority=req.priority,
            created_by=actor_ref(actor) or None,
        )
        db.add(key)
        db.add(
            ProviderKeyAudit(
                id=_new_id("pka"),
                provider_id=owner.id,
                key_id=key.id,
                actor_ref=actor_ref(actor) or None,
                action="created",
                reason=None,
            )
        )
        await db.commit()
        await db.refresh(key)
        return key

    async def list_keys(self, db: AsyncSession, provider_id: str) -> list[ProviderKey]:
        provider = await db.get(Provider, provider_id)
        if provider is None:
            raise EntityNotFound("Không tìm thấy nhà cung cấp.", code="provider_not_found")
        stmt = (
            select(ProviderKey)
            .where(key_scope(provider))
            .order_by(ProviderKey.created_at.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def revoke_key(
        self,
        db: AsyncSession,
        provider_id: str,
        key_id: str,
        actor: AuthActor,
        reason: str | None,
    ) -> ProviderKey:
        require_model_admin(actor)
        # Same lock order as runtime leases; credential audit FK checks must not
        # wait on a provider locked by a worker that is waiting for this key.
        owner = await credential_owner(db, provider_id, lock=True)
        key = (
            await db.execute(
                select(ProviderKey)
                .where(ProviderKey.id == key_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if key is None or key.provider_id != owner.id:
            raise EntityNotFound("Không tìm thấy credential.", code="provider_key_not_found")
        if key.status == "revoked":
            return key
        key.status = "revoked"
        db.add(
            ProviderKeyAudit(
                id=_new_id("pka"),
                provider_id=owner.id,
                key_id=key.id,
                actor_ref=actor_ref(actor) or None,
                action="revoked",
                reason=redact(reason) if reason else None,
            )
        )
        await db.commit()
        await db.refresh(key)
        return key

    async def rotate_key(
        self,
        db: AsyncSession,
        provider_id: str,
        key_id: str,
        req: KeyRotateRequest,
        actor: AuthActor,
    ) -> ProviderKey:
        require_model_admin(actor)
        owner = await credential_owner(db, provider_id, lock=True)
        old = (
            await db.execute(select(ProviderKey).where(ProviderKey.id == key_id).with_for_update())
        ).scalar_one_or_none()
        if old is None or old.provider_id != owner.id:
            raise EntityNotFound("Không tìm thấy credential.", code="provider_key_not_found")
        if old.status != "active":
            raise Conflict("Credential đã bị thu hồi.", code="provider_key_revoked")
        replacement = ProviderKey(
            id=_new_id("key"),
            provider_id=owner.id,
            model_ids=old.model_ids,
            name=req.name,
            secret_encrypted=encrypt(req.secret),
            masked_hint=mask_secret(req.secret),
            status="active",
            priority=req.priority,
            created_by=actor_ref(actor),
        )
        old.status = "revoked"
        db.add(replacement)
        db.add(
            ProviderKeyAudit(
                id=_new_id("pka"),
                provider_id=owner.id,
                key_id=old.id,
                actor_ref=actor_ref(actor),
                action="rotated",
                reason=redact(req.reason) if req.reason else None,
            )
        )
        db.add(
            ProviderKeyAudit(
                id=_new_id("pka"),
                provider_id=owner.id,
                key_id=replacement.id,
                actor_ref=actor_ref(actor),
                action="created",
            )
        )
        await db.commit()
        await db.refresh(replacement)
        return replacement

    async def audit(self, db: AsyncSession, provider_id: str, limit: int) -> list[ProviderKeyAudit]:
        owner = await credential_owner(db, provider_id)
        return list(
            (
                await db.execute(
                    select(ProviderKeyAudit)
                    .where(ProviderKeyAudit.provider_id == owner.id)
                    .order_by(ProviderKeyAudit.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )


key_service = KeyService()
