"""Structured Fact Layer — Exact numerical & tabular data retrieval without hallucinations."""

from __future__ import annotations

import logging
import re

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeCollection, KnowledgeDocument, KnowledgeFact

logger = logging.getLogger(__name__)


def count_subject_matches(attribute_value: str | None, subject_names: list[str] | None) -> int:
    """Count how many queried subjects appear together in a SINGLE combination (reverse-combo ranking).

    If attribute_value contains multiple combinations (e.g. "(Toán, Văn, Anh), (Văn, Anh, Hóa)"),
    we check each combination separately and take the maximum matches in any single combination.
    This prevents false-positive blending across different combinations of the same major.
    """
    if not attribute_value or not subject_names:
        return 0

    combos = re.findall(r"\(([^)]+)\)", attribute_value)
    if not combos:
        combos = [c.strip() for c in re.split(r"[;\n|/]", attribute_value) if c.strip()]
    if not combos:
        combos = [attribute_value]

    max_combo_matches = 0
    clean_subjects = [(s or "").strip().lower() for s in subject_names if (s or "").strip()]

    subject_aliases: dict[str, tuple[str, ...]] = {
        "tiếng anh": ("tiếng anh", "anh", "ngoại ngữ"),
        "anh": ("tiếng anh", "anh", "ngoại ngữ"),
        "lý": ("vật lý", "vật lí", "lý", "lí"),
        "hóa": ("hóa học", "hóa"),
        "sinh": ("sinh học", "sinh"),
        "văn": ("ngữ văn", "văn"),
        "sử": ("lịch sử", "sử"),
        "địa": ("địa lý", "địa lí", "địa"),
        "tin": ("tin học", "tin"),
        "toán": ("toán học", "toán"),
    }

    for combo in combos:
        lowered_combo = combo.lower()
        matched = 0
        for subj in clean_subjects:
            aliases = subject_aliases.get(subj, (subj,))
            if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", lowered_combo) for alias in aliases):
                matched += 1
        max_combo_matches = max(max_combo_matches, matched)

    return max_combo_matches


def _is_major_specific_fact(fact: KnowledgeFact | object) -> bool:
    """Determine if a fact record belongs to an individual major/program rather than institution-level policy."""
    entity_type = (getattr(fact, "entity_type", "") or "").lower()
    if entity_type in ("major", "admissions_major"):
        return True

    entity_name = getattr(fact, "entity_name", "") or ""
    if re.search(r"\b(?:mã\s*ngành|\d{7})\b", entity_name, re.IGNORECASE):
        return True
    if re.search(r"\bngành\s+[A-ZÀ-Ỹa-zà-ỹ]", entity_name):
        return True

    raw_data = getattr(fact, "raw_data", None)
    return bool(
        isinstance(raw_data, dict)
        and any(k in raw_data for k in ("major_code", "major_name", "program_code"))
    )


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
        subject_names: list[str] | None = None,
        target_entities: list[str] | None = None,
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

        # 2. Match target entity names if provided
        if target_entities:
            for te in target_entities:
                clean_te = te.strip()
                if clean_te:
                    conditions.append(KnowledgeFact.entity_name.ilike(f"%{clean_te}%"))

        # 3. Match keywords
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

        # 4. Optional attribute filter
        if fact_attributes:
            attr_conditions = [KnowledgeFact.attribute_name.ilike(f"%{attr}%") for attr in fact_attributes]
            query = query.where(or_(*attr_conditions))

        if tenant_id:
            query = query.where(KnowledgeCollection.tenant_id == tenant_id)
        if workspace_id:
            query = query.where(KnowledgeCollection.workspace_id == workspace_id)

        # Over-fetch when ranking by subjects so the best AND-matches survive the cut.
        fetch_limit = limit * 3 if subject_names else limit
        query = query.limit(fetch_limit)
        try:
            res = await db.execute(query)
            scalars = res.scalars()
            rows = list(scalars.all()) if hasattr(scalars, "all") else []
        except Exception as e:
            logger.debug("Fact lookup query skipped or failed: %s", e)
            return []

        if subject_names:
            clean_subjs = [s.strip().lower() for s in subject_names if s and s.strip()]
            rows.sort(
                key=lambda f: count_subject_matches(
                    getattr(f, "attribute_value", ""), clean_subjs
                ),
                reverse=True,
            )
        else:
            # Check if query specifically targeted any entity
            query_entity_markers: list[str] = []
            if entity_codes:
                query_entity_markers.extend([c.strip().lower() for c in entity_codes if c and c.strip()])
            if target_entities:
                query_entity_markers.extend([t.strip().lower() for t in target_entities if t and t.strip()])
            if keywords:
                common_attr_words = {
                    "phương thức", "tuyển sinh", "chỉ tiêu", "học phí", "điểm chuẩn",
                    "tổ hợp", "xét tuyển", "năm 2024", "năm 2025", "năm 2026", "2024", "2025", "2026",
                }
                for kw in keywords:
                    clean_kw = kw.strip().lower()
                    if len(clean_kw) >= 3 and clean_kw not in common_attr_words:
                        query_entity_markers.append(clean_kw)

            if not query_entity_markers:
                # General query: exclude major-specific facts that were matched merely by common attribute name
                rows = [f for f in rows if not _is_major_specific_fact(f)]
            else:
                # Entity-targeted query: only retain major-specific facts that match the requested entity
                def matches_entity(f: KnowledgeFact | object) -> bool:
                    if not _is_major_specific_fact(f):
                        return True
                    ent_name = (getattr(f, "entity_name", "") or "").lower()
                    attr_val = (getattr(f, "attribute_value", "") or "").lower()
                    raw = getattr(f, "raw_data", {}) or {}
                    raw_str = str(raw).lower() if isinstance(raw, dict) else ""
                    return any(
                        m in ent_name or m in attr_val or m in raw_str
                        for m in query_entity_markers
                    )
                rows = [f for f in rows if matches_entity(f)]

        return rows[:limit]

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
