"""Condition Route Node Handler — Evaluates intents and routes DAG execution."""

from __future__ import annotations

import re

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


class ConditionRouteNodeHandler(BaseNodeHandler):
    """Branches DAG execution based on intent matching rules."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        message = context.node_data.get("user_message", "").lower()
        config = node_spec.config or {}
        rules = config.get("rules", [])
        default_node = config.get("default_node")

        next_target = default_node
        matched_rule_id = None

        for rule in rules:
            match_spec = rule.get("match", {})
            pattern = match_spec.get("intent")
            if pattern:
                # Build safe word-boundary pattern to prevent false subword matches (e.g. 'hi' inside 'nhiêu')
                tokens = [t.strip() for t in pattern.split("|") if t.strip()]
                safe_regex = r"(?:^|\W)(?:" + "|".join(re.escape(t) for t in tokens) + r")(?:\W|$)"
                if re.search(safe_regex, message, re.IGNORECASE):
                    next_target = rule.get("to")
                    matched_rule_id = rule.get("id")
                    break

        context.node_data["routed_to"] = next_target
        context.node_data["matched_rule_id"] = matched_rule_id

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "next_node": next_target,
                "matched_rule_id": matched_rule_id,
            },
            next_node_override=next_target,
        )
