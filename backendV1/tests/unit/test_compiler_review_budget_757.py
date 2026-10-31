"""Review budget at the send boundary, replay identity and contract-invalid recovery.

These run the real ``_execute_segments``/``_run_segment`` code against the in-memory
review harness of the refinement tests, with a recording fake at the ``ChatModel`` port so
the exact messages handed to the adapter and every provider call are observable. Row
locking across real concurrent sessions is proven by the isolated-database integration
tests, not here.
"""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta

import pytest

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.compilation.review import artifacts, execution, parts, refinement, report
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage, ChatRequest, ChatResult
from tests.unit.test_compiler_review_refinement_755 import (
    _setup_segmented_harness,
    _truncation_error,
    _valid_assessment_json,
)


def _result(content: str, *, total_tokens: int | None = 320) -> ChatResult:
    return ChatResult(
        content=content,
        provider="openai-compatible",
        model="ollama/gpt-oss:120b",
        prompt_tokens=200,
        completion_tokens=120,
        finish_reason="stop",
        total_tokens=total_tokens,
        raw_body=json.dumps(
            {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}
        ).encode("utf-8"),
    )


class RecordingChat:
    """Records each provider call; ``handler(chat, incoming)`` returns a result or raises."""

    def __init__(self, handler=None) -> None:
        self.handler = handler or (lambda chat, incoming: _result(_valid_assessment_json(incoming)))
        self.messages: list[list[ChatMessage]] = []
        self.owned: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    @property
    def calls(self) -> int:
        return len(self.messages)

    async def complete(self, messages: list[ChatMessage], request: ChatRequest):
        incoming = json.loads(messages[-1].content)
        self.messages.append(list(messages))
        self.owned.append(
            (
                tuple(unit["id"] for unit in incoming["source_units"]),
                tuple(unit["id"] for unit in incoming["draft_units"]),
            )
        )
        return self.handler(self, incoming)


def _run(env, chat):
    return asyncio.run(
        execution._execute_segments(
            env.db,
            env.blob,
            chat,
            env.actor,
            env.run.workspace_id,
            env.run,
            env.review,
            env.material,
            env.runtime,
        )
    )


def _roots(env):
    return [seg for seg in env.db.segments if seg.parent_segment_id is None]


def _requests(env) -> int:
    return refinement._executed_request_count(env.db.segments)


def _scope_of(segment) -> tuple[list[str], list[str]]:
    return segment.scope["source_ids"], segment.scope["draft_ids"]


def _is_scope(incoming: dict, segment) -> bool:
    sources, drafts = _scope_of(segment)
    return [u["id"] for u in incoming["source_units"]] == sources and [
        u["id"] for u in incoming["draft_units"]
    ] == drafts


# --------------------------------------------------------------------------- P1: budget
def test_request_ceiling_below_planned_roots_stops_before_extra_send(monkeypatch):
    env = _setup_segmented_harness(
        monkeypatch, unit_count=18, refinement_policy={"max_requests": 1}
    )
    assert len(_roots(env)) >= 2
    chat = RecordingChat()
    with pytest.raises(AppException) as caught:
        _run(env, chat)
    assert caught.value.code == "compilation_review_budget_requests_exceeded"
    assert chat.calls == 1
    assert _requests(env) == 1
    assert env.review.status == "failed"  # a spent budget is decided, not uncertain
    completed = [seg for seg in env.db.segments if seg.status == "completed"]
    assert len(completed) == 1  # finished work is kept


def test_token_ceiling_counts_input_and_output_reservation(monkeypatch):
    # Fake budget reserves 4696 (input estimate + 4096 output); settled usage is 320.
    env = _setup_segmented_harness(
        monkeypatch, unit_count=18, refinement_policy={"max_tokens": 5000}
    )
    chat = RecordingChat()
    with pytest.raises(AppException) as caught:
        _run(env, chat)
    assert caught.value.code == "compilation_review_budget_tokens_exceeded"
    assert chat.calls == 1  # 320 observed + 4696 reserved would exceed 5000


def test_time_ceiling_is_cumulative_and_resume_cannot_reset_it(monkeypatch):
    env = _setup_segmented_harness(
        monkeypatch, unit_count=18, refinement_policy={"max_seconds": 60}
    )
    env.review.created_at = utcnow() - timedelta(seconds=300)
    env.review.trace["execution_elapsed_seconds"] = 0.0
    env.review.trace["execution_started_at"] = env.review.created_at.isoformat()
    chat = RecordingChat()
    with pytest.raises(AppException) as caught:
        _run(env, chat)
    assert caught.value.code == "compilation_review_budget_time_exceeded"
    assert chat.calls == 0

    # A new claim retains all spent time; completed/raw work remains reusable.
    env.review.trace = refinement.resume_execution_trace(env.review)
    env.review.status = "running"
    env.review.finished_at = None
    resumed = RecordingChat()
    with pytest.raises(AppException) as caught:
        _run(env, resumed)
    assert caught.value.code == "compilation_review_budget_time_exceeded"
    assert resumed.calls == 0


def test_refinement_children_and_resume_are_bounded_by_the_total_ceiling(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=34, root_part_target=2)
    roots = _roots(env)
    assert len(roots) >= 3, len(roots)
    target = roots[1]
    # Room for every root plus exactly one extra request: the split's second child and
    # the remaining root cannot both be sent.
    env.review.trace["refinement_policy"] = {"max_requests": len(roots) + 1}

    def handler(chat, incoming):
        if _is_scope(incoming, target) and chat.owned.count(chat.owned[-1]) == 1:
            raise _truncation_error(usage_tokens=900)
        return _result(_valid_assessment_json(incoming))

    chat = RecordingChat(handler)
    with pytest.raises(AppException) as caught:
        _run(env, chat)
    assert caught.value.code.startswith("compilation_review_")
    assert "exceeded" in caught.value.code
    assert chat.calls <= len(roots) + 1
    assert _requests(env) == chat.calls
    before = chat.calls

    # Rerunning under the same ceiling cannot send anything new or mint a request.
    env.review.status = "running"
    again = RecordingChat()
    with pytest.raises(AppException):
        _run(env, again)
    assert again.calls == 0
    assert before == _requests(env)

    # After the operator-level ceiling is raised, only unfinished leaves are sent.
    done = {seg.id for seg in env.db.segments if seg.status == "completed"}
    env.review.trace["refinement_policy"] = {"max_requests": 99}
    env.review.status = "running"
    finish = RecordingChat()
    _run(env, finish)
    assert env.review.status == "completed"
    assert all(seg.id in done or seg.status == "completed" for seg in env.db.segments)
    sent_scopes = set(finish.owned)
    for seg in env.db.segments:
        if seg.id in done:
            sources, drafts = _scope_of(seg)
            assert (tuple(sources), tuple(drafts)) not in sent_scopes


def test_completed_node_and_raw_replay_make_no_call_and_no_charge(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)
    first_chat = RecordingChat()
    _run(env, first_chat)
    assert env.review.status == "completed"
    requests = _requests(env)
    tokens = refinement.total_usage(env.db.segments)
    assert requests == first_chat.calls and tokens == 320 * requests

    # Replay: a stopped review whose leaves are all complete reuses stored results.
    env.review.status = "running"
    replay = RecordingChat()
    _run(env, replay)
    assert replay.calls == 0
    assert _requests(env) == requests
    assert refinement.total_usage(env.db.segments) == tokens

    # Local re-read of a received raw is not a provider attempt either.
    leaf = _roots(env)[0]
    leaf.status = "received"
    leaf.finished_at = None
    env.db.segment_artifacts[:] = [
        art
        for art in env.db.segment_artifacts
        if not (art.segment_id == leaf.id and art.kind in {"assessment_json", "markdown"})
    ]
    env.review.status = "running"
    reread = RecordingChat()
    _run(env, reread)
    assert reread.calls == 0
    assert _requests(env) == requests
    assert leaf.status == "completed"


def test_unknown_usage_stays_unknown_and_still_consumes_budget(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)
    chat = RecordingChat(
        lambda chat, incoming: _result(_valid_assessment_json(incoming), total_tokens=None)
    )
    _run(env, chat)
    assert env.review.status == "completed"
    assert refinement.total_usage(env.db.segments) is None  # never turned into 0
    assert env.review.usage_tokens is None
    entries = [e for seg in env.db.segments for e in refinement.attempts_of(seg)]
    assert entries and all(e["state"] == "usage_unknown" for e in entries)
    assert all(e["usage_tokens"] is None for e in entries)
    # Unknown consumption counts at its reserved bound, not at 0, against a ceiling.
    exposure = refinement._token_exposure(env.db.segments)
    assert exposure == 4696 * len(entries)
    limits = refinement.ReviewRefinementLimits(max_tokens=exposure + 4695)
    with pytest.raises(AppException) as caught:
        refinement.check_request_budget(
            env.review, env.db.segments, limits, estimate_tokens=4696
        )
    assert caught.value.code == "compilation_review_budget_tokens_exceeded"


def test_provider_uncertain_is_not_resent_and_marks_the_review_uncertain(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)

    def handler(chat, incoming):
        raise AppException("lost", code="chat_provider_uncertain", status_code=504)

    chat = RecordingChat(handler)
    with pytest.raises(AppException):
        _run(env, chat)
    assert chat.calls == 1
    assert env.review.status == "uncertain"
    leaf = _roots(env)[0]
    assert leaf.status == "uncertain"
    entry = refinement.attempts_of(leaf)[0]
    assert entry["state"] == "unknown" and entry["usage_tokens"] is None
    env.review.status = "running"
    again = RecordingChat()
    with pytest.raises(AppException):
        _run(env, again)
    assert again.calls == 0


# ----------------------------------------------------------------- P2: replay identity
def test_messages_sent_to_adapter_match_the_stored_hash_after_leaf_count_changes(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=34, root_part_target=2)
    roots = _roots(env)
    assert len(roots) >= 3
    target = roots[0]

    def handler(chat, incoming):
        if _is_scope(incoming, target) and chat.owned.count(chat.owned[-1]) == 1:
            raise _truncation_error(usage_tokens=900)
        return _result(_valid_assessment_json(incoming))

    chat = RecordingChat(handler)
    _run(env, chat)
    assert env.review.status == "completed"
    by_scope = {
        (tuple(seg.scope["source_ids"]), tuple(seg.scope["draft_ids"])): seg
        for seg in env.db.segments
    }
    assert len(env.review.trace["refinement_events"]) == 1
    for messages, owned in zip(chat.messages, chat.owned, strict=True):
        seg = by_scope[owned]
        replay = seg.scope["replay"]
        assert parts._sha(messages[0].content) == replay["prompt_sha256"]
        assert parts._sha(messages[-1].content) == seg.input_sha256
        # The instruction is independent of the (changed) leaf count.
        assert replay["prompt_version"] == parts.SEGMENT_PROMPT_VERSION
        assert "/" not in messages[0].content.split("#")[1][:3]


def test_legacy_prompt_replay_sends_the_verified_total_not_the_current_one(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)
    root = _roots(env)[0]
    scope = root.scope
    legacy = parts.build_part(
        env.material.payload,
        index=scope["index"],
        total=3,
        source_ids=scope["source_ids"],
        draft_ids=scope["draft_ids"],
        context_source_ids=scope["context_source_ids"],
        context_draft_ids=scope["context_draft_ids"],
        structured=False,
        projection=scope.get("projection", "compact/v3"),
        capacity=scope["budget"]["input_budget_tokens"],
        output_tokens=scope["budget"]["max_output_tokens"],
        prompt_version=parts.LEGACY_SEGMENT_PROMPT_VERSION,
    )
    root.scope = legacy.scope_dict()
    assert root.scope["request_total"] == 3
    # The live leaf count is now 8; a total taken from it would change the prompt.
    _plan, messages, _ = parts.rebuild_part(
        env.material.payload, root.scope, total=8, structured=False
    )
    assert f"phần {scope['index']}/3" in messages[0].content
    assert "/8" not in messages[0].content
    assert parts._sha(messages[0].content) == root.scope["replay"]["prompt_sha256"]

    # A stored scope that no longer matches is refused, never sent.
    broken = {**root.scope, "request_total": 8}
    with pytest.raises(AppException) as caught:
        parts.rebuild_part(env.material.payload, broken, total=8, structured=False)
    assert caught.value.code == "compilation_review_segment_mismatch"


# ------------------------------------------------------ P2: contract-invalid recovery
def _extra_context_or_unknown(incoming: dict, content: dict) -> dict:
    extra = (incoming.get("context_source_units") or [{"id": "context:unit"}])[0]["id"]
    content["source_assessments"].append(
        {
            "source_id": extra,
            "status": "out_of_scope",
            "draft_ids": [],
            "explanation": "Nhận xét thừa cho ngữ cảnh chỉ đọc.",
            "suggested_action": "",
        }
    )
    return content


def _missing_unit(incoming: dict, content: dict) -> dict:
    content["source_assessments"] = content["source_assessments"][1:] or []
    if not incoming["source_units"]:
        content["draft_assessments"] = content["draft_assessments"][1:]
    return content


def _bad_reference(incoming: dict, content: dict) -> dict:
    if content["draft_assessments"]:
        content["draft_assessments"][0]["source_ids"] = ["no:such:source"]
    else:
        content["source_assessments"][0]["draft_ids"] = ["no:such:draft"]
    return content


@pytest.mark.parametrize("breaker", [_extra_context_or_unknown, _missing_unit, _bad_reference])
def test_contract_invalid_part_is_recovered_by_splitting_only_that_part(monkeypatch, breaker):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)
    roots = _roots(env)
    target = roots[0]
    sibling = roots[1]
    assert target.segment_index != sibling.segment_index

    def handler(chat, incoming):
        content = json.loads(_valid_assessment_json(incoming))
        if _is_scope(incoming, target):
            content = breaker(incoming, content)
        return _result(json.dumps(content, ensure_ascii=False))

    chat = RecordingChat(handler)
    _run(env, chat)
    assert env.review.status == "completed"

    parent = target
    children = [seg for seg in env.db.segments if seg.parent_segment_id == parent.id]
    assert len(children) == 2
    assert parent.status == "completed" and parent.error_code is None
    assert parent.config["refined"] is True
    # Parent attempt, raw and failure trace are retained as history.
    assert any(
        art.segment_id == parent.id and art.kind == "raw_response"
        for art in env.db.segment_artifacts
    )
    assert any(
        art.segment_id == parent.id and art.kind == "assessment_json"
        for art in env.db.segment_artifacts
    )
    assert any(
        art.segment_id == parent.id and art.kind == "markdown"
        for art in env.db.segment_artifacts
    )
    failure = parent.config["last_failure"]
    assert failure["code"] == "compilation_review_invalid"
    assert failure["diagnosis"]["parsed"] is True
    event = env.review.trace["refinement_events"][0]
    assert event["reason"] == "compilation_review_invalid"
    assert event["parent_segment_id"] == parent.id

    # Exactly one provider call per failed parent / child / untouched sibling.
    parent_calls = [o for o in chat.owned if o == (tuple(parent.scope["source_ids"]), tuple(parent.scope["draft_ids"]))]
    assert len(parent_calls) == 1
    sibling_calls = [o for o in chat.owned if o == (tuple(sibling.scope["source_ids"]), tuple(sibling.scope["draft_ids"]))]
    assert len(sibling_calls) == 1
    # Ownership of the children is the exact partition of the parent's.
    refinement.verify_parent_child_coverage(env.db.segments)
    assert sorted(k for c in children for k in c.scope["source_ids"]) == sorted(
        parent.scope["source_ids"]
    )
    assert sorted(k for c in children for k in c.scope["draft_ids"]) == sorted(
        parent.scope["draft_ids"]
    )
    # The failed parent's observed usage still counts toward the review total.
    assert refinement.total_usage(env.db.segments) == 320 * _requests(env)


def test_extra_readonly_context_assessment_is_diagnosed_not_discarded(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)
    target = _roots(env)[0]
    seen: dict = {}

    def handler(chat, incoming):
        content = json.loads(_valid_assessment_json(incoming))
        if _is_scope(incoming, target) and "diagnosis" not in seen:
            seen["context"] = [u["id"] for u in incoming.get("context_source_units", [])]
            content["source_assessments"].append(
                {
                    "source_id": seen["context"][0] if seen["context"] else "context:unit",
                    "status": "uncertain",
                    "draft_ids": [],
                    "explanation": "x",
                    "suggested_action": "",
                }
            )
            seen["diagnosis"] = True
        return _result(json.dumps(content, ensure_ascii=False))

    chat = RecordingChat(handler)
    _run(env, chat)
    diagnosis = target.config["last_failure"]["diagnosis"]["source_assessments"]
    assert diagnosis["expected"] == len(target.scope["source_ids"])
    assert diagnosis["returned"] == diagnosis["expected"] + 1
    assert diagnosis["missing"] == 0
    assert diagnosis["extra_context"] + diagnosis["extra_unknown"] == 1
    # The surplus assessment is never trimmed to make the original response pass.
    raw_artifact = next(
        art
        for art in env.db.segment_artifacts
        if art.segment_id == target.id and art.kind == "raw_response"
    )
    stored = asyncio.run(env.blob.get_bytes(raw_artifact.blob_key))
    content = json.loads(json.loads(stored)["choices"][0]["message"]["content"])
    assert len(content["source_assessments"]) == diagnosis["returned"]


def test_recovery_budget_exhaustion_stops_stably_and_rerun_does_not_loop(monkeypatch):
    env = _setup_segmented_harness(
        monkeypatch, unit_count=18, refinement_policy={"max_contract_recoveries": 1}
    )

    def handler(chat, incoming):
        content = json.loads(_valid_assessment_json(incoming))
        content["draft_assessments"].append(
            {
                "draft_id": "not:owned",
                "status": "uncertain",
                "source_ids": [],
                "explanation": "x",
                "suggested_action": "",
            }
        )
        return _result(json.dumps(content, ensure_ascii=False))

    chat = RecordingChat(handler)
    with pytest.raises(AppException) as caught:
        _run(env, chat)
    assert caught.value.code == "compilation_review_recovery_exhausted"
    assert env.review.status == "failed"
    assert chat.calls == 2  # the parent, then one failed child; no unbounded retries
    calls_before = chat.calls
    requests_before = _requests(env)

    env.review.status = "running"
    again = RecordingChat(handler)
    with pytest.raises(AppException) as second:
        _run(env, again)
    assert second.value.code.startswith("compilation_review_")
    assert again.calls == 0  # the invalid raw is not re-read into new requests
    assert _requests(env) == requests_before == calls_before
    assert env.review.status == "failed"


def test_received_node_with_invalid_raw_is_recovered_without_a_new_request(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)
    target = _roots(env)[0]

    bad_once = RecordingChat(
        lambda chat, incoming: _result(
            json.dumps({"source_assessments": [], "draft_assessments": []})
        )
    )
    with pytest.raises(AppException):
        asyncio.run(
            execution._run_segment(
                env.db,
                env.blob,
                bad_once,
                env.actor,
                env.run.workspace_id,
                env.run,
                env.review,
                target,
                env.material,
                env.runtime,
                len(_roots(env)),
                "rex_token_755",
            )
        )
    assert target.status == "failed"
    # Mirror the interrupted run of the live review: received, raw on disk, never decided.
    target.status, target.error_code, target.finished_at = "received", None, None
    requests = _requests(env)

    chat = RecordingChat()
    _run(env, chat)
    assert env.review.status == "completed"
    parent_scope = (tuple(target.scope["source_ids"]), tuple(target.scope["draft_ids"]))
    assert parent_scope not in chat.owned  # the invalid raw was replayed locally only
    assert len(refinement.attempts_of(target)) == 1
    assert _requests(env) == requests + chat.calls


def test_decode_failure_is_stored_as_a_failed_node_with_raw_and_usage(monkeypatch):
    env = _setup_segmented_harness(monkeypatch, unit_count=18)
    env.review.trace["structured_output"] = True
    for seg in env.db.segments:
        scope = seg.scope
        plan = parts.build_part(
            env.material.payload,
            index=scope["index"],
            total=scope["request_total"],
            source_ids=scope["source_ids"],
            draft_ids=scope["draft_ids"],
            context_source_ids=scope["context_source_ids"],
            context_draft_ids=scope["context_draft_ids"],
            structured=True,
            projection=scope.get("projection", "compact/v3"),
            capacity=scope["budget"]["input_budget_tokens"],
            output_tokens=scope["budget"]["max_output_tokens"],
        )
        seg.scope = plan.scope_dict()
        seg.input_sha256, seg.schema_sha256 = plan.input_sha256, plan.schema_sha256
        seg.config = {**seg.config, "structured_output": True}
    target = _roots(env)[0]
    chat = RecordingChat(lambda chat, incoming: _result("{not json at all"))
    with pytest.raises(AppException) as caught:
        asyncio.run(
            execution._run_segment(
                env.db,
                env.blob,
                chat,
                env.actor,
                env.run.workspace_id,
                env.run,
                env.review,
                target,
                env.material,
                env.runtime,
                len(_roots(env)),
                "rex_token_755",
            )
        )
    assert caught.value.code == "compilation_review_invalid"
    assert target.status == "failed" and target.error_code == "compilation_review_invalid"
    assert target.usage_tokens == 320
    assert refinement.attempts_of(target)[0]["state"] == "settled"
    assert any(
        art.segment_id == target.id and art.kind == "raw_response"
        for art in env.db.segment_artifacts
    )
    assert target.config["last_failure"]["diagnosis"]["parsed"] is False


def test_report_diagnosis_separates_missing_extra_and_context_ids():
    payload = {
        "source_units": [{"id": "s1"}, {"id": "s2"}],
        "draft_units": [{"id": "d1"}],
        "context_source_units": [{"id": "ctx1"}],
    }
    content = json.dumps(
        {
            "source_assessments": [{"source_id": "s1"}, {"source_id": "ctx1"}, {"source_id": "zz"}],
            "draft_assessments": [{"draft_id": "d1"}],
        }
    )
    result = report.diagnose_contract(content, payload)
    assert result["source_assessments"] == {
        "expected": 2,
        "returned": 3,
        "missing": 1,
        "extra_context": 1,
        "extra_unknown": 1,
        "duplicates": 0,
    }
    assert result["draft_assessments"]["missing"] == 0
    assert report.diagnose_contract("not json", payload) == {"parsed": False}
    assert artifacts.SEGMENT_TYPES["raw_response"]  # raw history kind remains supported
