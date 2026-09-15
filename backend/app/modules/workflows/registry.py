"""Node Handler Registry for Workflow DAG Execution."""

from __future__ import annotations

import logging

from app.modules.workflows.nodes import (
    BaseNodeHandler,
    ChatInputNodeHandler,
    ConditionRouteNodeHandler,
    HumanApprovalNodeHandler,
    LLMGenerateNodeHandler,
    OutputChatNodeHandler,
    RAGAnswerNodeHandler,
)

logger = logging.getLogger(__name__)


class NodeHandlerRegistry:
    """Registry mapping node type strings to their respective execution handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, BaseNodeHandler] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        chat_input = ChatInputNodeHandler()
        self.register("input.chat", chat_input)
        self.register("chat_input", chat_input)

        condition_route = ConditionRouteNodeHandler()
        self.register("condition.route", condition_route)
        self.register("router", condition_route)

        rag_answer = RAGAnswerNodeHandler()
        self.register("core.knowledge.answer", rag_answer)
        self.register("rag.retrieval", rag_answer)
        self.register("rag.answer", rag_answer)
        self.register("knowledge_answer", rag_answer)

        llm_gen = LLMGenerateNodeHandler()
        self.register("llm.generate", llm_gen)
        self.register("modelops.generate", llm_gen)
        self.register("drafting.generate", llm_gen)
        self.register("question_bank.generate", llm_gen)

        output_chat = OutputChatNodeHandler()
        self.register("output.chat", output_chat)
        self.register("chat_output", output_chat)

        human_app = HumanApprovalNodeHandler()
        self.register("tool.human_approval", human_app)
        self.register("human.approval", human_app)

    def register(self, node_type: str, handler: BaseNodeHandler) -> None:
        self._handlers[node_type.lower().strip()] = handler

    def get(self, node_type: str) -> BaseNodeHandler | None:
        return self._handlers.get(node_type.lower().strip())


node_registry = NodeHandlerRegistry()
