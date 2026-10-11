"""Read-only API/DB verification of browser-created E2E test collections."""

import asyncio
import json
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)

COLLECTION_ID = "col_b04b7104008f"


async def main() -> None:
    evidence: dict = {"collection_id": COLLECTION_ID, "sources": [], "indices": []}
    async with AsyncSessionFactory() as db:
        sources = (
            await db.scalars(
                select(KnowledgeSourceRevision)
                .join(
                    KnowledgeBinding,
                    KnowledgeSourceRevision.binding_id == KnowledgeBinding.id,
                )
                .where(KnowledgeBinding.collection_id == COLLECTION_ID)
            )
        ).all()
        assert sources and all(source.normalizer_version == "v2" for source in sources)
        for source in sources:
            evidence["sources"].append(
                {
                    "id": source.id,
                    "version": source.normalizer_version,
                    "page_manifest": source.page_manifest,
                    "hash": source.canonical_hash,
                }
            )
        indices = (
            await db.scalars(
                select(KnowledgeIndexRevision)
                .join(
                    KnowledgeBinding,
                    KnowledgeIndexRevision.binding_id == KnowledgeBinding.id,
                )
                .where(
                    KnowledgeBinding.collection_id == COLLECTION_ID,
                    KnowledgeIndexRevision.status == "active",
                )
            )
        ).all()
        assert len(indices) == 2
        for index in indices:
            assert index.parity_report["parity_passed"]
            evidence["indices"].append(
                {
                    "id": index.id,
                    "chunk_count": index.chunk_count,
                    "source_revision_id": index.source_revision_v2_id,
                    "parity": index.parity_report,
                }
            )
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001", timeout=90) as client:
        login = await client.post(
            settings.API_PREFIX + "/auth/login", json={"access_key": settings.DEV_ACCESS_PASSWORD}
        )
        login.raise_for_status()
        query = "Trong bộ dữ liệu E2E341-PAGE2, học phí ngành Công nghệ thông tin là bao nhiêu?"
        response = await client.post(
            settings.API_PREFIX + "/rag/search",
            json={
                "query": query,
                "collection_id": COLLECTION_ID,
                "tenant_id": "tenant_qnu",
                "workspace_id": "workspace_qnu",
            },
        )
        response.raise_for_status()
        result = response.json()
        assert result["items"] and "21.341.000" in result["items"][0]["content"]
        assert result["items"][0]["page_number"] == 2
        assert all(
            not ("<!-- Trang 1 -->" in item["content"] and "<!-- Trang 2 -->" in item["content"])
            for item in result["items"]
        )
        evidence["search"] = result
        ask = await client.post(
            settings.API_PREFIX + "/rag/ask",
            json={"question": query, "collection_id": COLLECTION_ID},
        )
        evidence["ask"] = {"status_code": ask.status_code, "body": ask.json()}
        ask.raise_for_status()
        answer = ask.json()
        assert answer["status"] == "answered"
        assert "21.341.000" in answer["answer"]
        assert any(
            citation["page_number"] == 2 and "21.341.000" in citation["quote"]
            for citation in answer["citations"]
        )
    target = (
        Path(__file__).resolve().parents[1]
        / "storage"
        / "e2e_fixtures"
        / "341"
        / "live_verification.json"
    )
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "search_status": response.status_code,
                "found": result["total_found"],
                "first_page": result["items"][0]["page_number"],
                "ask_status": ask.status_code,
                "active_chunks": sum(index["chunk_count"] for index in evidence["indices"]),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
