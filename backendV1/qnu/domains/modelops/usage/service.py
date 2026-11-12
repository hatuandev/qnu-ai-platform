"""UTC monthly usage accounting and idempotent inference reservations."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.models import ModelOpsEvent, ModelUsageRecord, WorkspaceQuota
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound


def month_start(period: date | None = None) -> date:
    return (period or datetime.now(UTC).date()).replace(day=1)


async def locked_quota(
    db: AsyncSession, workspace_id: str, period: date, *, create: bool = False
) -> WorkspaceQuota:
    if create:
        await db.execute(
            insert(WorkspaceQuota)
            .values(
                workspace_id=workspace_id,
                month_period=period,
                tokens_used=0,
                tokens_reserved=0,
                is_blocked=False,
            )
            .on_conflict_do_nothing()
        )
    quota = (
        await db.execute(
            select(WorkspaceQuota)
            .where(
                WorkspaceQuota.workspace_id == workspace_id, WorkspaceQuota.month_period == period
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if quota is None:
        raise Conflict("Không tìm thấy bản ghi tổng hợp sử dụng.", code="usage_period_missing")
    return quota


class UsageService:
    async def configuration_events(
        self, db: AsyncSession, actor: AuthActor, limit: int
    ) -> list[ModelOpsEvent]:
        require_model_admin(actor)
        return list(
            (
                await db.execute(
                    select(ModelOpsEvent).order_by(ModelOpsEvent.created_at.desc()).limit(limit)
                )
            )
            .scalars()
            .all()
        )

    async def read_quota(
        self, db: AsyncSession, actor: AuthActor, workspace_id: str, period: date
    ) -> WorkspaceQuota | None:
        await resolve_workspace_access(db, actor, workspace_id, allow_suspended=True)
        return await db.get(WorkspaceQuota, (workspace_id, month_start(period)))

    async def list_usage(
        self, db: AsyncSession, actor: AuthActor, workspace_id: str, page: int, page_size: int
    ) -> tuple[list[ModelUsageRecord], int]:
        await resolve_workspace_access(
            db, actor, workspace_id, required_roles=("admin",), allow_suspended=True
        )
        condition = ModelUsageRecord.workspace_id == workspace_id
        total = int(
            (
                await db.execute(
                    select(func.count()).select_from(ModelUsageRecord).where(condition)
                )
            ).scalar_one()
        )
        rows = (
            (
                await db.execute(
                    select(ModelUsageRecord)
                    .where(condition)
                    .order_by(ModelUsageRecord.created_at.desc(), ModelUsageRecord.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def initialize_legacy_period(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        period: date,
    ) -> WorkspaceQuota:
        require_model_admin(actor)
        await resolve_workspace_access(
            db, actor, workspace_id, for_update=True, allow_suspended=True
        )
        quota = await locked_quota(db, workspace_id, month_start(period), create=True)
        quota.monthly_token_limit = None
        quota.is_blocked = False
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="quota.updated",
            detail={"month": quota.month_period.isoformat(), "monthly_limits_enabled": False},
        )
        await db.commit()
        await db.refresh(quota)
        return quota

    async def reserve(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        capability: str,
        request_id: str,
        request_hash: str,
        token_budget: int,
        provider_id: str | None = None,
        *,
        document_ocr: bool = False,
        index_run_id: str | None = None,
    ) -> ModelUsageRecord:
        if (
            not request_id
            or len(request_id) > 128
            or type(token_budget) is not int
            or token_budget < (0 if document_ocr else 1)
            or token_budget > 10**15
            or not re.fullmatch(r"[0-9a-f]{64}", request_hash)
        ):
            raise AppException("Reservation không hợp lệ.", code="usage_request_invalid")
        await resolve_workspace_access(db, actor, workspace_id, for_update=True)
        provider = await catalog_service.resolve_provider(
            db, actor, workspace_id, capability, provider_id, index_run_id=index_run_id
        )
        if document_ocr and (
            provider.provider_type != "mineru" or capability != "ocr" or token_budget != 0
        ):
            raise AppException("Reservation OCR không hợp lệ.", code="usage_request_invalid")
        ref = actor_ref(actor)
        quota = await locked_quota(db, workspace_id, month_start(), create=True)
        old = (
            await db.execute(
                select(ModelUsageRecord).where(
                    ModelUsageRecord.workspace_id == workspace_id,
                    ModelUsageRecord.request_id == request_id,
                )
            )
        ).scalar_one_or_none()
        if old:
            if (
                old.request_hash,
                old.actor_ref,
                old.provider_id,
                old.capability,
                old.reserved_tokens,
            ) != (request_hash, ref, provider.id, capability, token_budget):
                raise Conflict("Request ID đã dùng cho yêu cầu khác.", code="idempotency_conflict")
            await db.commit()
            return old
        quota.tokens_reserved += token_budget
        record = ModelUsageRecord(
            id="usage_" + uuid.uuid4().hex[:16],
            workspace_id=workspace_id,
            provider_id=provider.id,
            actor_ref=ref,
            request_id=request_id,
            request_hash=request_hash,
            capability=capability,
            model_name=provider.model_name,
            month_period=quota.month_period,
            reserved_tokens=token_budget,
            status="reserved",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def settle(
        self,
        db: AsyncSession,
        usage_id: str,
        *,
        total_tokens: int | None,
        cost_usd: Decimal | None = None,
        failed: bool = False,
    ) -> ModelUsageRecord:
        """No HTTP write endpoint: only trusted, measured provider results may call this.

        NULL tokens preserve the reservation until reconciliation. This prevents
        a timeout with uncertain billing from being treated as a free request.
        """
        if (
            total_tokens is not None
            and (type(total_tokens) is not int or total_tokens < 0 or total_tokens > 10**15)
        ) or (cost_usd is not None and (not cost_usd.is_finite() or cost_usd < 0)):
            raise AppException("Usage không hợp lệ.", code="usage_invalid")
        record = await db.get(ModelUsageRecord, usage_id)
        if record is None:
            raise EntityNotFound("Không tìm thấy lượt sử dụng.", code="usage_not_found")
        quota = await locked_quota(db, record.workspace_id, record.month_period)
        record = (
            await db.execute(
                select(ModelUsageRecord)
                .where(ModelUsageRecord.id == usage_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        status = "unknown" if total_tokens is None else ("failed" if failed else "completed")
        if record.status in ("completed", "failed"):
            if (record.total_tokens, record.cost_usd, record.status) != (
                total_tokens,
                cost_usd,
                status,
            ):
                raise Conflict("Usage đã được ghi với giá trị khác.", code="usage_already_settled")
        else:
            if total_tokens is not None:
                quota.tokens_reserved -= record.reserved_tokens
                quota.tokens_used += total_tokens
            record.total_tokens, record.cost_usd, record.status = total_tokens, cost_usd, status
        await db.commit()
        await db.refresh(record)
        return record


usage_service = UsageService()
