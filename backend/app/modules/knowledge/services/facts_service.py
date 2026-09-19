"""Knowledge Structured Facts Service — Excel/CSV parsing and structured facts management."""

from __future__ import annotations

import hashlib
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.knowledge.excel_parser import parse_excel_facts
from app.modules.knowledge.models import KnowledgeDocument, KnowledgeFact
from app.modules.knowledge.schemas import (
    FactExcelImportResponse,
    FactItemResponse,
    FactListResponse,
)
from app.modules.knowledge.services.collection_service import collection_service

logger = logging.getLogger(__name__)


class FactsService:
    """Service managing structured facts extraction, Excel imports, and queries."""

    async def import_facts_from_excel(
        self,
        db: AsyncSession,
        collection_id: str,
        file_bytes: bytes,
        filename: str,
    ) -> FactExcelImportResponse:
        """Import structured facts from an Excel spreadsheet into knowledge_facts."""
        await collection_service.get_collection(db, collection_id)

        parsed_facts = parse_excel_facts(file_bytes, filename)
        if not parsed_facts:
            raise AppException(
                "Không trích xuất được bảng biểu số liệu từ tệp tải lên.",
                code="excel_parse_failed",
            )

        file_hash = hashlib.sha256(file_bytes).hexdigest()
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Save original file to storage
        storage_path = f"collections/{collection_id}/{doc_id}_{filename}"
        await storage_service.save(storage_path, file_bytes)

        # Create representative knowledge document
        doc = KnowledgeDocument(
            id=doc_id,
            collection_id=collection_id,
            title=f"Bảng biểu số hóa: {filename}",
            file_name=filename,
            file_type="xlsx" if filename.endswith(".xlsx") else "csv",
            file_size_bytes=len(file_bytes),
            file_hash=file_hash,
            version=1,
            status="ready",
            is_active=True,
            storage_path=storage_path,
        )
        db.add(doc)

        imported_count = 0
        for item in parsed_facts:
            fact = KnowledgeFact(
                id=f"fct_{uuid.uuid4().hex[:12]}",
                collection_id=collection_id,
                document_id=doc.id,
                entity_name=item["entity_name"],
                entity_type=item["entity_type"],
                attribute_name=item["attribute_name"],
                attribute_value=item["attribute_value"],
                confidence=item.get("confidence", 1.0),
                raw_data=item.get("raw_data", {}),
            )
            db.add(fact)
            imported_count += 1

        await db.commit()
        logger.info(
            "Imported %d facts from %s into collection %s",
            imported_count,
            filename,
            collection_id,
        )

        return FactExcelImportResponse(
            collection_id=collection_id,
            imported_count=imported_count,
            document_id=doc.id,
            message=f"Đã nạp thành công {imported_count} mục số hóa từ tệp {filename}.",
        )

    async def get_collection_facts(
        self,
        db: AsyncSession,
        collection_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> FactListResponse:
        """Query structured facts belonging to a collection."""
        await collection_service.get_collection(db, collection_id)

        count_res = await db.execute(
            select(func.count(KnowledgeFact.id)).where(KnowledgeFact.collection_id == collection_id)
        )
        total = count_res.scalar() or 0

        query = (
            select(KnowledgeFact)
            .where(KnowledgeFact.collection_id == collection_id)
            .order_by(KnowledgeFact.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        facts = list((await db.execute(query)).scalars().all())

        return FactListResponse(
            collection_id=collection_id,
            total=total,
            facts=[
                FactItemResponse(
                    id=f.id,
                    collection_id=f.collection_id,
                    document_id=f.document_id,
                    entity_name=f.entity_name,
                    entity_type=f.entity_type,
                    attribute_name=f.attribute_name,
                    attribute_value=f.attribute_value,
                    confidence=f.confidence,
                    raw_data=f.raw_data or {},
                    created_at=f.created_at,
                )
                for f in facts
            ],
        )


facts_service = FactsService()
