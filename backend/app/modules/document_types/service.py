"""Async service for the canonical QNU document taxonomy."""

from __future__ import annotations

import logging
import unicodedata
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, EntityAlreadyExistsError, EntityNotFoundError
from app.modules.document_types.catalog import (
    CATEGORY_NAMES,
    document_type_source_hash,
    normalize_document_type_code,
)
from app.modules.document_types.models import DocumentType
from app.modules.document_types.schemas import (
    DocumentTypeCreateRequest,
    DocumentTypeResponse,
    DocumentTypeSyncResponse,
    DocumentTypeUpdateRequest,
)
from app.modules.document_types.seed_data import DOCUMENT_TYPE_SEED_DATA, DOCUMENT_TYPE_SEED_VERSION

logger = logging.getLogger(__name__)

TAXONOMY_VERSION = DOCUMENT_TYPE_SEED_VERSION
SOURCE_SYSTEM = "qnu-ai-core"


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return unicodedata.normalize("NFC", value.strip())


def _to_response(record: DocumentType, doc_count: int = 0) -> DocumentTypeResponse:
    return DocumentTypeResponse(
        id=record.code,
        code=record.code,
        name=record.name,
        category=record.category,
        category_name=CATEGORY_NAMES.get(record.category, record.category),
        description=record.description,
        priority=record.priority,
        retention_period=record.retention_period,
        nd30=record.nd30,
        is_active=record.is_active,
        is_system_default=record.is_system_default,
        is_custom=record.is_custom,
        doc_count=doc_count,
        source_system=record.source_system,
        source_version=record.source_version,
        source_hash=record.source_hash,
        synced_at=record.synced_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class DocumentTypeService:
    """Manage taxonomy rows and synchronize the qnu-ai-core catalog."""

    async def list_document_types(
        self,
        db: AsyncSession,
        search: str | None = None,
        category: str | None = None,
        active_only: bool = False,
    ) -> list[DocumentTypeResponse]:
        if category and category not in CATEGORY_NAMES:
            raise AppException(
                f"Nhóm loại văn bản '{category}' không hợp lệ.",
                code="document_type_category_invalid",
                details={"category": category},
            )
        query = select(DocumentType).order_by(DocumentType.priority.desc(), DocumentType.name)
        if search and search.strip():
            pattern = f"%{_clean_text(search).casefold()}%"
            query = query.where(
                func.lower(DocumentType.code).like(pattern)
                | func.lower(DocumentType.name).like(pattern)
            )
        if category:
            query = query.where(DocumentType.category == category)
        if active_only:
            query = query.where(DocumentType.is_active.is_(True))

        records = list((await db.execute(query)).scalars().all())
        if not records:
            return []

        from app.modules.knowledge.models import KnowledgeDocument

        knowledge_document = KnowledgeDocument
        codes = [record.code for record in records]
        counts_result = await db.execute(
            select(knowledge_document.document_type_code, func.count(knowledge_document.id))
            .where(
                knowledge_document.document_type_code.in_(codes),
                knowledge_document.is_active.is_(True),
            )
            .group_by(knowledge_document.document_type_code)
        )
        counts = {code: count for code, count in counts_result.all()}
        return [_to_response(record, counts.get(record.code, 0)) for record in records]

    async def get_document_type(self, db: AsyncSession, code: str) -> DocumentTypeResponse:
        normalized_code = normalize_document_type_code(code) or code.strip()
        record = await db.get(DocumentType, normalized_code)
        if not record:
            raise EntityNotFoundError(
                f"Loại văn bản '{code}' không tồn tại.",
                details={"document_type_code": code},
            )
        from app.modules.knowledge.models import KnowledgeDocument

        knowledge_document = KnowledgeDocument
        count_result = await db.execute(
            select(func.count(knowledge_document.id)).where(
                knowledge_document.document_type_code == record.code,
                knowledge_document.is_active.is_(True),
            )
        )
        return _to_response(record, count_result.scalar_one())

    async def create_document_type(
        self, db: AsyncSession, request: DocumentTypeCreateRequest
    ) -> DocumentTypeResponse:
        code = _clean_text(request.code)
        if code is None:
            raise AppException("Mã loại văn bản không được để trống.", code="document_type_invalid")
        existing = await db.get(DocumentType, code)
        if existing:
            raise EntityAlreadyExistsError(
                f"Mã loại văn bản '{code}' đã tồn tại.",
                details={"document_type_code": code},
            )

        now = datetime.now(UTC)
        record = DocumentType(
            code=code,
            name=_clean_text(request.name) or request.name,
            category=request.category,
            description=_clean_text(request.description),
            priority=request.priority,
            retention_period=_clean_text(request.retention_period),
            nd30=False,
            is_active=True,
            is_system_default=False,
            is_custom=True,
            source_system="platform",
            source_version=None,
            source_hash=None,
            synced_at=now,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("Created custom document type code=%s", record.code)
        return _to_response(record)

    async def update_document_type(
        self, db: AsyncSession, code: str, request: DocumentTypeUpdateRequest
    ) -> DocumentTypeResponse:
        record = await self._get_record(db, code)
        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if isinstance(value, str):
                value = _clean_text(value)
            setattr(record, field_name, value)
        await db.commit()
        await db.refresh(record)
        logger.info("Updated document type code=%s", record.code)
        return await self.get_document_type(db, record.code)

    async def deactivate_document_type(self, db: AsyncSession, code: str) -> DocumentTypeResponse:
        record = await self._get_record(db, code)
        record.is_active = False
        await db.commit()
        await db.refresh(record)
        logger.info("Deactivated document type code=%s", record.code)
        return await self.get_document_type(db, record.code)

    async def validate_active_code(self, db: AsyncSession, code: str | None) -> str | None:
        """Validate a user-supplied code before a document is persisted."""
        if code is None or not code.strip():
            return None
        normalized_code = normalize_document_type_code(code) or code.strip()
        record = await db.get(DocumentType, normalized_code)
        if not record:
            raise AppException(
                f"Loại văn bản '{code}' không được hỗ trợ.",
                code="document_type_invalid",
                details={"document_type_code": code},
            )
        if not record.is_active:
            raise AppException(
                f"Loại văn bản '{record.name}' đang bị vô hiệu hóa.",
                code="document_type_inactive",
                details={"document_type_code": record.code},
            )
        return record.code

    async def sync_from_catalog(
        self, db: AsyncSession, taxonomy_version: str = TAXONOMY_VERSION
    ) -> DocumentTypeSyncResponse:
        """Idempotently upsert qnu-ai-core definitions and audit their source hash."""
        source_hash = document_type_source_hash()
        synced_at = datetime.now(UTC)
        added = 0
        updated = 0
        skipped = 0
        catalog_codes = {definition["code"] for definition in DOCUMENT_TYPE_SEED_DATA}

        for definition in DOCUMENT_TYPE_SEED_DATA:
            record = await db.get(DocumentType, definition["code"])
            if record and record.is_custom:
                skipped += 1
                continue
            if not record:
                record = DocumentType(code=definition["code"])
                db.add(record)
                added += 1
            else:
                has_catalog_changes = any(
                    getattr(record, field_name) != definition[field_name]
                    for field_name in (
                        "name",
                        "category",
                        "description",
                        "priority",
                        "retention_period",
                        "nd30",
                        "is_active",
                        "is_system_default",
                        "is_custom",
                        "source_system",
                    )
                )
                has_audit_changes = record.source_version != taxonomy_version or record.source_hash != source_hash
                updated += int(
                    has_catalog_changes or has_audit_changes
                )
            record.name = definition["name"]
            record.category = definition["category"]
            record.description = definition["description"]
            record.priority = definition["priority"]
            record.retention_period = definition["retention_period"]
            record.nd30 = definition["nd30"]
            record.is_active = definition["is_active"]
            record.is_system_default = definition["is_system_default"]
            record.is_custom = definition["is_custom"]
            record.source_system = definition["source_system"]
            record.source_version = taxonomy_version
            record.source_hash = source_hash
            record.synced_at = synced_at

        obsolete_result = await db.execute(
            select(DocumentType).where(
                DocumentType.is_custom.is_(False),
                DocumentType.is_active.is_(True),
                ~DocumentType.code.in_(catalog_codes),
            )
        )
        deactivated = 0
        for record in obsolete_result.scalars().all():
            record.is_active = False
            record.synced_at = synced_at
            deactivated += 1

        await db.commit()
        logger.info(
            "Synchronized document taxonomy version=%s added=%d updated=%d deactivated=%d",
            taxonomy_version,
            added,
            updated,
            deactivated,
        )
        return DocumentTypeSyncResponse(
            taxonomy_version=taxonomy_version,
            source_system=SOURCE_SYSTEM,
            source_hash=source_hash,
            added=added,
            updated=updated,
            deactivated=deactivated,
            skipped=skipped,
            total=len(DOCUMENT_TYPE_SEED_DATA),
            synced_at=synced_at,
        )

    async def _get_record(self, db: AsyncSession, code: str) -> DocumentType:
        normalized_code = normalize_document_type_code(code) or code.strip()
        record = await db.get(DocumentType, normalized_code)
        if not record:
            raise EntityNotFoundError(
                f"Loại văn bản '{code}' không tồn tại.",
                details={"document_type_code": code},
            )
        return record


document_types_service = DocumentTypeService()
