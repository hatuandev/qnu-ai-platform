"""Enable the approved evidence policy without changing published sources."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.core.evidence_policy import EvidenceSourcePreference
from app.modules.assistants.models import AssistantModel
from app.modules.assistants.schemas import AssistantLifecycleConfig
from app.modules.knowledge.models import KnowledgeCollection
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.retriever import hybrid_retriever


async def main():
    async with AsyncSessionFactory() as db:
        assistant = (await db.execute(select(AssistantModel).where(AssistantModel.code == "admissions").with_for_update())).scalar_one()
        collection = await db.get(KnowledgeCollection, assistant.collection_id, with_for_update=True)
        assert collection.tenant_id == assistant.tenant_id
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, collection.id,
            tenant_id=collection.tenant_id, workspace_id=collection.workspace_id)
        blocks = await load_published_blocks(db, snapshot)
        # This is a one-time configured contact, supported by the current published corpus.
        contact = "1800.55.88.49"
        proofs = [b for b in blocks if contact in b.text]
        assert proofs, "Do not configure an unsupported referral contact"
        before = {"config": assistant.config, "metadata": collection.collection_metadata,
                  "assistant_updated_at": assistant.updated_at.isoformat(), "snapshot": snapshot.model_dump(mode="json")}
        backup = Path("storage/evidence417_before.json")
        if not backup.exists():
            backup.write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
        config = AssistantLifecycleConfig.model_validate(assistant.config)
        config.knowledge_policy.evidence_policy.enabled = True
        config.knowledge_policy.evidence_policy.reference_year_mode = "current_year"
        preferred = "ks_rev_6280c8de7f46"
        superseded = "ks_rev_f122689af572"
        source_ids = {b.source_revision_id for b in blocks}
        assert {preferred, superseded}.issubset(source_ids), "Approved revisions must still be published"
        config.knowledge_policy.evidence_policy.source_preferences = [EvidenceSourcePreference(
            preferred_source_revision_id=preferred, superseded_source_revision_ids=[superseded], years=[2026],
            authorization_note="Người quản trị xác nhận ngày 2026-10-13: Ưu tiên TB 1906 cập nhật cho thông tin cùng ngữ cảnh; thay flyer đầu mùa chỉ khi cùng năm và cùng thông tin.")]
        config.guardrails.no_answer_message = (
            "Trong nguồn đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho phần thông tin bạn hỏi. "
            f"Bạn có thể liên hệ tư vấn tuyển sinh QNU qua {contact} để được xác nhận.")
        assistant.config = config.model_dump(mode="json")
        assistant.updated_at = datetime.now(UTC).replace(tzinfo=None)
        collection.collection_metadata = {**(collection.collection_metadata or {}), "evidence_answers_enabled": True}
        await db.commit()
        print(json.dumps({"assistant": assistant.code, "policy": config.knowledge_policy.evidence_policy.model_dump(),
            "sources": len(snapshot.binding_revisions), "epoch": snapshot.collection_epoch,
            "contact_source": {"binding_id": proofs[0].binding_id, "revision": proofs[0].source_revision_id,
                               "page": proofs[0].page_number}}, ensure_ascii=True))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
