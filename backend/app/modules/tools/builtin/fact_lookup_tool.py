"""Universal Fact Layer Query & Structured Data Lookup Tool — QNU AI Platform.

Enables any AI Assistant to query verified structured facts (benchmarks, tuition fees,
quotas, academic regulations, library policies) from PostgreSQL knowledge_facts table.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import or_, select

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeFact
from app.modules.tools.builtin.base import BaseTool

logger = logging.getLogger(__name__)


class FactLayerLookupTool(BaseTool):
    """Platform-wide tool for looking up verified structured facts from knowledge collections."""

    @property
    def name(self) -> str:
        return "lookup_fact_layer"

    @property
    def display_name(self) -> str:
        return "Tra Cứu Dữ Liệu Fact Layer Số Hóa"

    @property
    def description(self) -> str:
        return (
            "Tra cứu các dữ kiện, bảng số liệu, chỉ tiêu và quy định số hóa chính thức "
            "từ Kho tri thức của Trường Đại học Quy Nhơn (điểm chuẩn tuyển sinh, học phí, "
            "học bổng, điều kiện tốt nghiệp, giờ mở cửa thư viện...)."
        )

    @property
    def category(self) -> str:
        return "knowledge"

    def get_openapi_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Từ khóa hoặc tên đối tượng cần tra cứu (ví dụ: Công nghệ thông tin, thang điểm, học phí, hạn mượn sách)",
                        "default": "",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "Mã bộ sưu tập tri thức (mặc định lấy theo cấu hình của Trợ lý)",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Loại dữ kiện cần lọc (ví dụ: cutoff_score, tuition_fee, academic_scale...)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng bản ghi tối đa trả về",
                        "default": 20,
                    },
                },
                "required": [],
            },
        }

    async def _query_facts(
        self,
        db: Any,
        collection_id: str,
        entity_type: str | None,
        keyword: str,
        limit: int,
    ) -> dict[str, Any]:
        stmt = select(KnowledgeFact).where(KnowledgeFact.collection_id == collection_id)
        if entity_type:
            stmt = stmt.where(KnowledgeFact.entity_type == entity_type)
        if keyword:
            stmt = stmt.where(
                or_(
                    KnowledgeFact.entity_name.ilike(f"%{keyword}%"),
                    KnowledgeFact.attribute_value.ilike(f"%{keyword}%"),
                    KnowledgeFact.attribute_name.ilike(f"%{keyword}%"),
                )
            )
        stmt = stmt.limit(limit)
        res = await db.execute(stmt)
        facts = res.scalars().all()

        records = [
            {
                "entity_name": f.entity_name,
                "entity_type": f.entity_type,
                "attribute_name": f.attribute_name,
                "attribute_value": f.attribute_value,
                "raw_data": f.raw_data,
            }
            for f in facts
        ]

        return {
            "status": "success",
            "found": len(records) > 0,
            "collection_id": collection_id,
            "total_facts": len(records),
            "facts": records,
            "message": (
                f"Đã tìm thấy {len(records)} dữ kiện trong Kho tri thức ({collection_id})."
                if records
                else f"Không tìm thấy dữ kiện nào khớp với từ khóa '{keyword}' trong Kho tri thức ({collection_id})."
            ),
        }

    async def execute(
        self, parameters: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        keyword = (parameters.get("keyword") or "").strip()
        collection_id = (
            parameters.get("collection_id")
            or (context or {}).get("collection_id")
            or "col_admissions"
        )
        entity_type = parameters.get("entity_type")
        limit = min(50, max(1, parameters.get("limit", 20)))

        db_session = (context or {}).get("db_session")
        try:
            if db_session is not None:
                return await self._query_facts(db_session, collection_id, entity_type, keyword, limit)
            async with AsyncSessionFactory() as db:
                return await self._query_facts(db, collection_id, entity_type, keyword, limit)
        except Exception as exc:
            logger.warning("Failed to lookup facts: %s", exc)
            return {
                "status": "error",
                "found": False,
                "collection_id": collection_id,
                "facts": [],
                "message": f"Lỗi truy vấn Kho tri thức: {exc}",
            }
