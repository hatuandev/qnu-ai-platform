"""Read wired data without falling back to unrelated shared node results."""

from typing import Any

from app.core.exceptions import AppException
from app.modules.workflows.nodes.base import WorkflowContext


def routed_payload(context: WorkflowContext, node_id: str) -> dict[str, Any]:
    ports = context.node_inputs.get(node_id, {})
    envelope = ports.get("input", {})
    if isinstance(envelope, list):
        raise AppException(
            f"Node '{node_id}' cần cổng riêng cho nhiều nguồn đầu vào.",
            code="WORKFLOW_INPUT_PORT_AMBIGUOUS",
            status_code=422,
        )
    sources = context.node_input_sources.get(node_id, [])
    payload = (
        {
            key: value
            for key, value in sources[0].items()
            if key
            in (
                "citations",
                "status",
                "contexts",
                "facts_used",
                "suggested_questions",
                "artifacts",
                "warnings",
                "missing_fields",
            )
        }
        if len(sources) == 1
        else {}
    )
    payload.update(dict(envelope) if isinstance(envelope, dict) else {"input": envelope})
    payload.update({key: value for key, value in ports.items() if key != "input"})
    return payload


def routed_text(context: WorkflowContext, node_id: str, names: tuple[str, ...], legacy: str) -> str:
    payload = routed_payload(context, node_id)
    for name in (*names, "input"):
        if name not in payload:
            continue
        value = payload[name]
        if not isinstance(value, str) or not value.strip():
            raise AppException(
                f"Node '{node_id}' nhận văn bản không hợp lệ tại cổng '{name}'.",
                code="WORKFLOW_INPUT_INVALID",
                status_code=422,
            )
        return value
    # Unported legacy control edges (approval/router) carry no text.
    ports = context.node_inputs.get(node_id, {})
    if any(key != "input" for key in ports):
        raise AppException(
            f"Node '{node_id}' không có cổng văn bản phù hợp.",
            code="WORKFLOW_INPUT_INVALID",
            status_code=422,
        )
    return legacy
