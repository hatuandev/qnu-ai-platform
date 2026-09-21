"""Tests for multi-turn query rewrite resolution and modelops provider safety."""

from __future__ import annotations

import pytest

from app.core.exceptions import AppException
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.providers.local_vllm_adapter import LocalVLLMAdapter
from app.modules.modelops.schemas import ChatMessage
from app.modules.modelops.services.inference_service import (
    NON_CHAT_MODEL_KEYWORDS,
    VALID_CHAT_PROVIDER_TYPES,
)
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.nodes.query_rewrite_node import (
    QueryRewriteNodeHandler,
    resolve_multiturn_query,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


def test_resolve_multiturn_affirmative_short_response() -> None:
    """Short affirmative queries like 'có tôi muốn' must be resolved to the topic offered by the assistant."""
    history = [
        {
            "role": "user",
            "content": "bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?",
        },
        {
            "role": "assistant",
            "content": (
                "Chào bạn! Ngành Công nghệ thông tin xét tuyển các tổ hợp: (Toán, Anh, Lý)...\n"
                "Bạn có muốn mình chia sẻ thêm thông tin về chỉ tiêu tuyển sinh hoặc các phương thức xét tuyển áp dụng cho ngành này không?"
            ),
        },
    ]

    resolved_1 = resolve_multiturn_query("có tôi muốn", history)
    assert resolved_1 is not None
    assert "chỉ tiêu" in resolved_1.lower()
    assert "phương thức" in resolved_1.lower()
    assert "công nghệ thông tin" in resolved_1.lower()

    resolved_2 = resolve_multiturn_query("có", history)
    assert resolved_2 is not None
    assert "công nghệ thông tin" in resolved_2.lower()

    resolved_3 = resolve_multiturn_query("vâng", history)
    assert resolved_3 is not None
    assert "công nghệ thông tin" in resolved_3.lower()


def test_resolve_multiturn_pronoun_reference() -> None:
    """Pronoun references like 'ngành này' must be replaced with the active major."""
    history = [
        {
            "role": "user",
            "content": "ngành Kỹ thuật phần mềm ra trường làm gì?",
        },
        {
            "role": "assistant",
            "content": "Sinh viên ngành Kỹ thuật phần mềm có thể làm lập trình viên, kỹ sư kiểm thử...",
        },
    ]

    resolved = resolve_multiturn_query("học phí của ngành này là bao nhiêu?", history)
    assert resolved is not None
    assert "kỹ thuật phần mềm" in resolved.lower()
    assert "ngành này" not in resolved.lower()


@pytest.mark.asyncio
async def test_query_rewrite_node_handler_resolves_multiturn_in_workflow() -> None:
    """QueryRewriteNodeHandler must rewrite 'có tôi muốn' using conversation_history in context."""
    handler = QueryRewriteNodeHandler()
    spec = WorkflowNodeSpec(
        id="query_rewrite",
        type="query.rewrite",
        config={"use_fast_rules": True, "use_llm": False},
    )
    ctx = WorkflowContext(
        workflow_id="test_flow",
        tenant_id="tenant_qnu",
        conversation_id="conv_123",
        inputs={
            "message": "có tôi muốn",
            "conversation_history": [
                {
                    "role": "user",
                    "content": "ngành công nghệ thông tin tuyển sinh thế nào",
                },
                {
                    "role": "assistant",
                    "content": "Bạn có muốn mình chia sẻ thêm thông tin về chỉ tiêu tuyển sinh hoặc các phương thức xét tuyển cho ngành này không?",
                },
            ],
        },
    )

    res = await handler.execute(spec, ctx)
    assert res.status == "completed"
    normalized = res.output["normalized_query"]
    assert "Công nghệ thông tin" in normalized
    assert "chỉ tiêu" in normalized.lower()
    assert ctx.node_data["normalized_query"] == normalized


def test_provider_safety_valid_chat_types() -> None:
    """InferenceService must exclude non-chat provider types."""
    assert "system_routing" not in VALID_CHAT_PROVIDER_TYPES
    assert "sentence_transformers" not in VALID_CHAT_PROVIDER_TYPES
    assert "docling" not in VALID_CHAT_PROVIDER_TYPES
    assert "bge-" in NON_CHAT_MODEL_KEYWORDS
    assert "embed" in NON_CHAT_MODEL_KEYWORDS
    assert "rerank" in NON_CHAT_MODEL_KEYWORDS


def test_get_llm_adapter_rejects_unsupported_provider() -> None:
    """get_llm_adapter must raise ValueError for unsupported provider types."""
    with pytest.raises(ValueError, match="Unsupported LLM provider type"):
        get_llm_adapter("system_routing", "@cf/baai/bge-m3")

    with pytest.raises(ValueError, match="Unsupported LLM provider type"):
        get_llm_adapter("docling", "docling-tableformer-local")


@pytest.mark.asyncio
async def test_local_vllm_adapter_fails_loudly_when_offline() -> None:
    """LocalVLLMAdapter must raise AppException when server is offline, not returning a mock string."""
    adapter = LocalVLLMAdapter(
        model_name="qwen2.5-7b-instruct",
        base_url="http://127.0.0.1:59999/v1",  # Guaranteed closed port
        timeout_seconds=1,
    )
    with pytest.raises(AppException) as exc_info:
        await adapter.generate([ChatMessage(role="user", content="Xin chào")])
    assert exc_info.value.code == "local_llm_unavailable"
    assert exc_info.value.status_code == 502
