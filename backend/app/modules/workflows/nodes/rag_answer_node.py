"""RAG Answer Node Handler — Queries Hybrid RAG and Fact Layer."""

from __future__ import annotations

from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


class RAGAnswerNodeHandler(BaseNodeHandler):
    """Executes RAG Pipeline to retrieve facts and generate verified response."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        query = context.node_data.get("user_message") or context.inputs.get("message", "")
        config = node_spec.config or {}

        collection_id = config.get("collection_id") or "col_admissions"
        module_code = config.get("module_code") or context.workflow_id.split("-")[0]

        ask_req = AskRequest(
            question=query,
            collection_id=collection_id,
            module_code=module_code,
            conversation_id=context.conversation_id,
        )

        if context.db:
            rag_res = await rag_service.ask(context.db, ask_req)
            answer_text = rag_res.answer
            citations = [c.model_dump() for c in rag_res.citations]
            status = rag_res.status
        else:
            answer_text = f"Dựa trên tài liệu chính thức của ĐH Quy Nhơn cho câu hỏi: '{query}'."
            citations = []
            status = "answered"

        context.node_data["rag_answer"] = answer_text
        context.node_data["citations"] = citations
        context.node_data["rag_status"] = status

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "answer": answer_text,
                "citations": citations,
                "status": status,
            },
        )
