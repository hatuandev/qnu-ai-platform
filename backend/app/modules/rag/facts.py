"""Structured Fact Layer — Exact numerical & tabular data retrieval without hallucinations."""

from __future__ import annotations

import logging

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeDocument, KnowledgeFact

logger = logging.getLogger(__name__)


class FactLayer:
    """Retrieves structured tabular records (Cutoff scores, Quotas, Fees, Rules) directly from DB."""

    async def lookup_facts(
        self,
        db: AsyncSession,
        collection_id: str,
        keywords: list[str],
        limit: int = 10,
    ) -> list[KnowledgeFact]:
        """Look up fact records matching any of the identified keywords."""
        if not keywords:
            return []

        conditions = []
        for kw in keywords:
            clean_kw = kw.strip().lower()
            if len(clean_kw) >= 2:
                conditions.append(KnowledgeFact.entity_name.ilike(f"%{clean_kw}%"))
                conditions.append(KnowledgeFact.attribute_name.ilike(f"%{clean_kw}%"))

        if not conditions:
            return []

        lifecycle_filter = or_(
            and_(
                KnowledgeDocument.id.is_not(None),
                KnowledgeDocument.is_active.is_(True),
                KnowledgeDocument.status.in_(["approved", "completed", "processed", "ready"]),
            ),
            KnowledgeDocument.id.is_(None),
        )

        query = (
            select(KnowledgeFact)
            .outerjoin(
                KnowledgeDocument,
                KnowledgeFact.document_id == KnowledgeDocument.id,
            )
            .where(
                KnowledgeFact.collection_id == collection_id,
                lifecycle_filter,
                or_(*conditions),
            )
            .limit(limit)
        )
        try:
            res = await db.execute(query)
            scalars = res.scalars()
            if hasattr(scalars, "all"):
                return list(scalars.all())
            return []
        except Exception as e:
            logger.debug("Fact lookup query skipped or failed: %s", e)
            return []

    @staticmethod
    def format_facts_as_markdown(facts: list[KnowledgeFact]) -> str:
        """Render retrieved fact items into a clean Markdown table."""
        if not facts:
            return ""

        headers = ["Thực thể / Ngành", "Thuộc tính", "Giá trị dữ liệu"]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for f in facts:
            lines.append(f"| {f.entity_name} | {f.attribute_name} | **{f.attribute_value}** |")

        return "\n".join(lines)


fact_layer = FactLayer()
