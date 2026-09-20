"""Structured Fact Layer — Exact numerical & tabular data retrieval without hallucinations."""

from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeCollection, KnowledgeDocument, KnowledgeFact

logger = logging.getLogger(__name__)


class FactLayer:
    """Retrieves structured tabular records (Cutoff scores, Quotas, Fees, Rules) directly from DB."""

    async def lookup_facts(
        self,
        db: AsyncSession,
        collection_id: str,
        keywords: list[str] | None = None,
        entity_codes: list[str] | None = None,
        fact_attributes: list[str] | None = None,
        limit: int = 15,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
    ) -> list[KnowledgeFact]:
        """Look up fact records matching identified keywords or entity codes, strictly bound to approved documents."""
        conditions = []

        # 1. Match specific entity codes (e.g. 7480107, 6.8, IELTS)
        if entity_codes:
            for code in entity_codes:
                clean_code = code.strip()
                if clean_code:
                    conditions.append(KnowledgeFact.entity_name.ilike(f"%{clean_code}%"))
                    conditions.append(KnowledgeFact.attribute_value.ilike(f"%{clean_code}%"))

        # 2. Match keywords
        if keywords:
            for kw in keywords:
                clean_kw = kw.strip().lower()
                if len(clean_kw) >= 2:
                    conditions.append(KnowledgeFact.entity_name.ilike(f"%{clean_kw}%"))
                    conditions.append(KnowledgeFact.attribute_name.ilike(f"%{clean_kw}%"))

        if not conditions:
            return []

        query = (
            select(KnowledgeFact)
            .join(
                KnowledgeDocument,
                KnowledgeFact.document_id == KnowledgeDocument.id,
            )
            .join(
                KnowledgeCollection,
                KnowledgeFact.collection_id == KnowledgeCollection.id,
            )
            .where(
                KnowledgeFact.collection_id == collection_id,
                KnowledgeDocument.is_active.is_(True),
                KnowledgeDocument.status.in_(["approved", "ready"]),
                or_(*conditions),
            )
        )

        # 3. Optional attribute filter
        if fact_attributes:
            attr_conditions = [KnowledgeFact.attribute_name.ilike(f"%{attr}%") for attr in fact_attributes]
            query = query.where(or_(*attr_conditions))

        if tenant_id:
            query = query.where(KnowledgeCollection.tenant_id == tenant_id)
        if workspace_id:
            query = query.where(KnowledgeCollection.workspace_id == workspace_id)

        query = query.limit(limit)
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
