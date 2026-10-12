"""Real DB + ModelOps + assistant workflow smoke, no config/reparse/publication writes.

Chat creates normal traces/conversations/usage. This is service-runtime E2E,
not browser/auth E2E. Run outside sandbox for Tailscale inference endpoints.
"""

import asyncio
import json
import sys

from app.core.database import AsyncSessionFactory
from app.modules.assistants.runtime import build_runtime_profile, resolve_runtime_scope
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.service import assistant_service
from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service

sys.stdout.reconfigure(encoding="utf-8")


async def main():
    async with AsyncSessionFactory() as db:
        assistant = await assistant_service.get_assistant(db, "admissions")
        profile = build_runtime_profile(assistant)
        tenant, workspace = await resolve_runtime_scope(db, assistant)
        if "--inspect" in sys.argv:
            from sqlalchemy import select

            from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
            from app.modules.knowledge.services.source_artifact import build_source_artifact
            from app.modules.knowledge.services.source_pages import manifest_page_count
            from app.modules.rag.retriever import hybrid_retriever

            snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, assistant.collection_id, tenant_id=tenant, workspace_id=workspace)
            print(json.dumps({"snapshot": snapshot.model_dump()}, ensure_ascii=False))
            bindings = (await db.execute(select(KnowledgeBinding).where(KnowledgeBinding.collection_id == assistant.collection_id))).scalars().all()
            for binding in bindings:
                source = await db.get(KnowledgeSourceRevision, binding.active_source_revision_id)
                if not source:
                    continue
                artifact = build_source_artifact(source.canonical_markdown or "", manifest_page_count(source.page_manifest), source.citation_metadata or {})
                print(json.dumps({"binding": binding.id, "source": source.id, "index": binding.active_index_revision_id,
                    "status": binding.status, "source_status": source.status, "facts": len(artifact["facts"]), "issues": artifact["issues"][:3],
                    "tables": [{"id": table["id"], "headers": table["headers"], "rows": table["rows"][:2]} for table in artifact["tables"]],
                    "targeted_facts": [fact for fact in artifact["facts"] if "7480201" in str(fact.get("raw_data", {}).get("entity_code")) or "IELTS" in fact["entity_name"]]}, ensure_ascii=False))
                text = source.canonical_markdown or ""
                position = text.find("7480201", text.find("2024"))
                print(json.dumps({"excerpt": text[max(0, position - 450):position + 800]}, ensure_ascii=False))
            return
        questions = ["Điểm chuẩn Công nghệ thông tin năm 2024 và năm 2025 là bao nhiêu?",
                     "Điểm chuẩn chính thức Công nghệ thông tin năm 2026 là bao nhiêu?",
                     "IELTS 6.0 quy đổi thành bao nhiêu điểm?"]
        for question in questions:
            req = AskRequest(question=question, collection_id=assistant.collection_id, module_code="admissions",
                             tenant_id=tenant, workspace_id=workspace, preferred_model_name=profile.model_policy.primary_model,
                             preferred_provider_id=getattr(profile.model_policy, "preferred_provider_id", None),
                             assistant_code=assistant.code, runtime_policy=profile.model_dump(mode="json"))
            for repeat in range(2):
                result = await rag_service.ask(db, req)
                print(json.dumps({"route": "rag", "repeat": repeat, "question": question,
                                  "status": result.status, "answer": result.answer,
                                  "decision": result.answer_decision}, ensure_ascii=False), flush=True)
            result = await assistant_service.chat(db, "admissions", AssistantChatRequest(message=question), correlation_id="smoke387")
            print(json.dumps({"route": "dag", "question": question, "status": result.status,
                              "answer": result.answer}, ensure_ascii=False), flush=True)
        message = questions[1]
        tokens, done = [], None
        async for event in assistant_service.chat_stream(db, "admissions", AssistantChatRequest(message=message, stream=True), correlation_id="smoke387-sse"):
            if event.startswith("event: token"):
                tokens.append(json.loads(event.split("data: ", 1)[1])["delta"])
            elif event.startswith("event: done"):
                done = json.loads(event.split("data: ", 1)[1])
            elif event.startswith("event: error"):
                print(event, flush=True)
        print(json.dumps({"route": "dag-sse", "question": message, "tokens": "".join(tokens), "done": done}, ensure_ascii=False), flush=True)


asyncio.run(main())
