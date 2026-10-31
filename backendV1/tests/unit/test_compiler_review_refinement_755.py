"""Regression tests for Batch 2 (review truncation refinement & recovery) and Batch 3 (deterministic merge & coverage)."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import (
    artifacts,
    execution,
    parts,
    refinement,
    service,
)
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
    CompilationReviewSegmentArtifact,
    ReviewArtifact,
)
from qnu.domains.modelops.capacity.schemas import ModelTokenLimits
from qnu.domains.modelops.public_api import ChatRuntime
from qnu.domains.modelops.reasoning import ReasoningDirective
from qnu.platform.errors import AppException, Conflict
from qnu.ports.chat_model import ChatMessage, ChatRequest, ChatResponseError, ChatResult


class MemoryBlobStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    async def put_bytes(self, key: str, data: bytes, content_type: str = "") -> None:
        self.objects[key] = bytes(data)
        self.content_types[key] = content_type

    async def get_bytes(self, key: str) -> bytes:
        if key not in self.objects:
            raise FileNotFoundError(key)
        return self.objects[key]


class InMemoryReviewDB:
    """Lightweight async session harness tracking CompilationReview, segments, and artifacts."""

    def __init__(self, review: CompilationReview, run: CompilationRun) -> None:
        self.review = review
        self.run = run
        self.segments: list[CompilationReviewSegment] = []
        self.review_artifacts: list[ReviewArtifact] = []
        self.segment_artifacts: list[CompilationReviewSegmentArtifact] = []
        self.commits = 0
        self.rollbacks = 0

    @property
    def no_autoflush(self):
        class _Noop:
            def __enter__(self):
                return None

            def __exit__(self, *args):
                return False

        return _Noop()

    def add(self, obj) -> None:
        if isinstance(obj, CompilationReviewSegment) and obj not in self.segments:
            self.segments.append(obj)
        elif isinstance(obj, ReviewArtifact) and obj not in self.review_artifacts:
            self.review_artifacts.append(obj)
        elif (
            isinstance(obj, CompilationReviewSegmentArtifact)
            and obj not in self.segment_artifacts
        ):
            self.segment_artifacts.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, obj, with_for_update: bool = False) -> None:
        return None

    async def get(self, model, ident: str, **kwargs):
        if model is CompilationReview and ident == self.review.id:
            return self.review
        if model is CompilationRun and ident == self.run.id:
            return self.run
        if model is CompilationReviewSegment:
            for seg in self.segments:
                if seg.id == ident:
                    return seg
        return None


def _build_material_payload(unit_count: int = 8) -> dict:
    source_units = [
        {
            "id": f"ocr_1:ev_{idx}",
            "kind": "paragraph",
            "ocr_run_id": "ocr_1",
            "page": 1,
            "text": f"Dữ kiện tuyển sinh ngành {idx}: chỉ tiêu {100 + idx}.",
            "requires_review": False,
        }
        for idx in range(1, unit_count + 1)
    ]
    draft_units = [
        {
            "id": "title",
            "kind": "title",
            "text": "Tổng hợp chỉ tiêu tuyển sinh 2026",
        },
        {
            "id": "section:1:heading",
            "kind": "heading",
            "text": "Danh mục ngành đào tạo",
        },
        *[
            {
                "id": f"section:1:paragraph:{idx}",
                "kind": "paragraph",
                "section": 1,
                "heading": "Danh mục ngành đào tạo",
                "text": f"Ngành {idx} có chỉ tiêu tuyển sinh năm 2026 là {100 + idx}.",
                "citations": [f"ocr_1:ev_{idx}"],
            }
            for idx in range(1, unit_count + 1)
        ],
    ]
    return {
        "topic": "Chỉ tiêu tuyển sinh 2026",
        "documents": [{"ocr_run_id": "ocr_1", "identity": {"revision_id": "rev_1"}}],
        "source_units": source_units,
        "draft_units": draft_units,
    }


def _valid_assessment_json(part_payload: dict) -> str:
    sources = part_payload["source_units"]
    drafts = part_payload["draft_units"]
    allowed_sources = part_payload.get("allowed_source_ids") or [u["id"] for u in sources]
    allowed_drafts = part_payload.get("allowed_draft_ids") or [u["id"] for u in drafts]
    content = {
        "source_assessments": [
            {
                "source_id": unit["id"],
                "status": "covered" if allowed_drafts else "out_of_scope",
                "draft_ids": allowed_drafts[:1],
                "explanation": "Đã đối chiếu đầy đủ trong phần này.",
                "suggested_action": "",
            }
            for unit in sources
        ],
        "draft_assessments": [
            {
                "draft_id": unit["id"],
                "status": "supported" if allowed_sources else "uncertain",
                "source_ids": (unit.get("citations") or allowed_sources[:1])[:1],
                "explanation": "Khớp với dữ kiện nguồn được dẫn chiếu.",
                "suggested_action": "",
            }
            for unit in drafts
        ],
    }
    return json.dumps(content, ensure_ascii=False)


def _truncation_error(*, usage_tokens: int | None = 4096) -> ChatResponseError:
    base = AppException(
        "Đầu ra chat bị cắt; chưa có bản nháp đầy đủ.",
        code="chat_output_truncated",
        status_code=422,
    )
    raw = json.dumps(
        {
            "choices": [{"message": {"content": '{"partial":'}, "finish_reason": "length"}],
            "usage": {"total_tokens": usage_tokens} if usage_tokens is not None else {},
        }
    ).encode("utf-8")
    return ChatResponseError(base, raw, usage_tokens)


def _setup_segmented_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    unit_count: int = 8,
    root_part_target: int = 2,
    refinement_policy: dict | None = None,
):
    payload = _build_material_payload(unit_count=unit_count)
    actor = AuthActor(
        actor_id="user:usr_editor",
        actor_type="user",
        username="editor",
        email="editor@qnu.edu.vn",
        is_platform_admin=False,
    )
    run = CompilationRun(
        id="cmp_test_755",
        workspace_id="ws_test",
        collection_id="col_test",
        status="completed",
        provider_id="prv_test",
    )
    reasoning = ReasoningDirective(
        mode="effort",
        parameter="reasoning_effort",
        value="low",
        level="low",
        policy_sha256="pol_sha_755",
    )
    runtime = ChatRuntime(
        provider_id="prv_test",
        provider_name="Test Provider",
        provider_type="openai_compatible",
        model_name="ollama/gpt-oss:120b",
        base_url="https://qnu-9router.duckdns.org/v1",
        timeout_seconds=60,
        api_key="test-key",
        token_limits=ModelTokenLimits(context_window_tokens=131072, max_output_tokens=4096),
        capacity_status="declared",
        workspace_id="ws_test",
        routing_trace=(),
    )
    all_plans = parts.plan_parts(
        payload,
        capacity=120000,
        output_tokens=4096 if root_part_target == 1 else 1600,
        structured=False,
        reasoning_shares_budget=True,
    )
    now = utcnow()
    review = CompilationReview(
        id="rvw_test_755",
        compilation_run_id=run.id,
        workspace_id=run.workspace_id,
        collection_id=run.collection_id,
        created_by="user:usr_editor",
        idempotency_key="idem_755",
        request_hash="req_hash_755",
        status="running",
        provider_id=runtime.provider_id,
        input_sha256="in_sha_755",
        draft_sha256="dr_sha_755",
        bundle_sha256="bd_sha_755",
        created_at=now,
        expires_at=now + timedelta(minutes=30),
        trace={
            "literal_check_version": 1,
            "review_concurrency": 1,
            "execution_token": "rex_token_755",
            "provider_id": runtime.provider_id,
            "model_name": runtime.model_name,
            "configuration_hash": runtime.configuration_hash,
            "max_output_tokens": 4096,
            "structured_output": False,
            "reasoning": reasoning.public_dict(),
            "segmentation": {
                "planner_version": parts.PLANNER_VERSION,
                "prompt_version": parts.SEGMENT_PROMPT_VERSION,
                "segment_count": len(all_plans),
                "manifest_sha256": None,
            },
            **({"refinement_policy": refinement_policy} if refinement_policy else {}),
        },
    )
    blob = MemoryBlobStore()
    db = InMemoryReviewDB(review, run)
    manifest = parts.manifest_for(
        review,
        all_plans,
        payload,
        capacity=120000,
        output_tokens=4096,
        reasoning_shares_budget=True,
    )
    manifest_bytes = json_bytes(manifest)
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    review.trace["segmentation"]["manifest_sha256"] = manifest_sha
    blob_key = (
        f"v1/workspaces/{review.workspace_id}/compilation-review/"
        f"{review.id}/segment_manifest/{manifest_sha}"
    )
    blob.objects[blob_key] = manifest_bytes
    db.add(
        ReviewArtifact(
            id="rva_manifest",
            review_id=review.id,
            kind="segment_manifest",
            blob_key=blob_key,
            sha256=manifest_sha,
            size_bytes=len(manifest_bytes),
            content_type="application/json",
        )
    )
    cfg = {
        "provider_id": runtime.provider_id,
        "configuration_hash": runtime.configuration_hash,
        "max_output_tokens": 4096,
        "structured_output": False,
        "reasoning": reasoning.public_dict(),
    }
    for plan in all_plans:
        db.add(
            CompilationReviewSegment(
                id=f"rvs_root_{plan.index}",
                review_id=review.id,
                parent_segment_id=None,
                segment_index=plan.index,
                status="pending",
                attempt_count=0,
                scope=plan.scope_dict(),
                input_sha256=plan.input_sha256,
                prompt_version=parts.SEGMENT_PROMPT_VERSION,
                schema_sha256=plan.schema_sha256,
                config=dict(cfg),
                request_hash=f"req_seg_{plan.index}",
            )
        )

    settled_records: list[dict] = []

    async def fake_load_segments(_db, _review_id):
        return sorted(db.segments, key=lambda item: item.segment_index)

    async def fake_store(_db, _blob, row, kind, data):
        sha = hashlib.sha256(data).hexdigest()
        for existing in db.review_artifacts:
            if existing.review_id == row.id and existing.kind == kind:
                if existing.sha256 != sha:
                    raise Conflict(
                        "Artifact conflict", code="compilation_review_artifact_conflict"
                    )
                return existing
        key = f"v1/workspaces/{row.workspace_id}/compilation-review/{row.id}/{kind}/{sha}"
        await _blob.put_bytes(key, data, artifacts.TYPES[kind])
        art = ReviewArtifact(
            id=f"rva_{kind}_{len(db.review_artifacts) + 1}",
            review_id=row.id,
            kind=kind,
            blob_key=key,
            sha256=sha,
            size_bytes=len(data),
            content_type=artifacts.TYPES[kind],
        )
        db.add(art)
        return art

    async def fake_read(_db, _blob, row, kind):
        for existing in db.review_artifacts:
            if existing.review_id == row.id and existing.kind == kind:
                data = await _blob.get_bytes(existing.blob_key)
                return existing, data
        raise AppException(
            "Missing artifact", code="compilation_review_artifact_missing", status_code=404
        )

    async def fake_segment_artifact(_db, segment_id, kind):
        for existing in db.segment_artifacts:
            if existing.segment_id == segment_id and existing.kind == kind:
                return existing
        return None

    async def fake_store_segment(_db, _blob, row, segment, kind, data):
        sha = hashlib.sha256(data).hexdigest()
        existing = await fake_segment_artifact(_db, segment.id, kind)
        if existing is not None:
            if existing.sha256 != sha:
                raise Conflict(
                    "Segment artifact conflict",
                    code="compilation_review_segment_artifact_conflict",
                )
            return existing
        key = (
            f"v1/workspaces/{row.workspace_id}/compilation-review/{row.id}/segments/"
            f"{segment.segment_index:04d}/{kind}/{sha}"
        )
        await _blob.put_bytes(key, data, artifacts.SEGMENT_TYPES[kind])
        art = CompilationReviewSegmentArtifact(
            id=f"rvsa_{segment.segment_index}_{kind}",
            segment_id=segment.id,
            kind=kind,
            blob_key=key,
            sha256=sha,
            size_bytes=len(data),
            content_type=artifacts.SEGMENT_TYPES[kind],
        )
        db.add(art)
        return art

    async def fake_read_segment(_db, _blob, segment, kind):
        existing = await fake_segment_artifact(_db, segment.id, kind)
        if existing is None:
            raise AppException(
                "Missing segment artifact",
                code="compilation_review_segment_artifact_missing",
                status_code=404,
            )
        data = await _blob.get_bytes(existing.blob_key)
        return existing, data

    async def fake_checkpoint(_db, _blob, _actor, row, _run):
        if row.status != "running" or row.expires_at <= utcnow():
            raise Conflict(
                "Lượt review đã hết thời gian chờ.", code="compilation_review_expired"
            )

    async def fake_require_provider(_db, _ws_id, _prv_id, expected_hash):
        if runtime.configuration_hash != expected_hash:
            raise Conflict(
                "Model review đã thay đổi.", code="compilation_review_provider_changed"
            )

    async def fake_prepare_chat_request(_db, _actor, _ws_id, messages, **kwargs):
        req = ChatRequest(
            endpoint=runtime.base_url,
            model=runtime.model_name,
            max_output_tokens=kwargs.get("max_output_tokens", 4096),
            timeout_seconds=runtime.timeout_seconds,
            api_key="test-key",
        )
        budget = SimpleNamespace(
            estimated_input_tokens=500,
            max_output_tokens=kwargs.get("max_output_tokens", 4096),
            safety_margin_tokens=100,
            total_reserved_tokens=4696,
            context_window_tokens=131072,
        )
        live_runtime = SimpleNamespace(
            provider_id=runtime.provider_id,
            configuration_hash=runtime.configuration_hash,
            reasoning_directive=lambda _task: reasoning,
        )
        return live_runtime, req, budget

    async def fake_reserve(
        _db, _actor, _ws_id, _cap, idemp_key, _req_hash, reserved, _prv_id
    ):
        rec = SimpleNamespace(
            id=f"usg_{len(settled_records) + 1}",
            idempotency_key=idemp_key,
            reserved_tokens=reserved,
            total_tokens=None,
            status="reserved",
        )
        settled_records.append({"record": rec, "settled": False})
        return rec

    async def fake_settle(_db, usage_id, *, total_tokens, failed: bool = False):
        for item in settled_records:
            if item["record"].id == usage_id:
                item["record"].total_tokens = total_tokens
                item["record"].status = (
                    "unknown"
                    if total_tokens is None
                    else ("failed" if failed else "completed")
                )
                item["settled"] = True

    async def fake_record_event(*args, **kwargs):
        return None

    async def fake_untouched(_db, _review_id):
        for seg in db.segments:
            if seg.attempt_count or seg.request_started_at is not None:
                return False
        return True

    monkeypatch.setattr(execution, "_load_segments", fake_load_segments)
    monkeypatch.setattr(artifacts, "store", fake_store)
    monkeypatch.setattr(artifacts, "read", fake_read)
    monkeypatch.setattr(artifacts, "segment_artifact", fake_segment_artifact)
    monkeypatch.setattr(artifacts, "store_segment", fake_store_segment)
    monkeypatch.setattr(artifacts, "read_segment", fake_read_segment)
    monkeypatch.setattr(service, "checkpoint", fake_checkpoint)
    monkeypatch.setattr(service, "untouched", fake_untouched)
    monkeypatch.setattr(execution, "require_provider", fake_require_provider)
    monkeypatch.setattr(execution, "prepare_chat_request", fake_prepare_chat_request)
    monkeypatch.setattr(execution.usage_service, "reserve", fake_reserve)
    monkeypatch.setattr(execution.usage_service, "settle", fake_settle)
    monkeypatch.setattr(execution, "record_workspace_event", fake_record_event)

    material = SimpleNamespace(
        payload=payload,
        bundle=SimpleNamespace(
            input_sha256=review.input_sha256,
            draft_sha256=review.draft_sha256,
            bundle_sha256=review.bundle_sha256,
        ),
    )
    return SimpleNamespace(
        db=db,
        blob=blob,
        actor=actor,
        run=run,
        review=review,
        material=material,
        runtime=runtime,
        settled_records=settled_records,
    )


def test_truncated_segment_creates_children_and_completed_sibling_is_never_rerun(
    monkeypatch,
):
    """Batch 2 (1, 2, 3, 9) & Batch 3: Truncated segment splits into children; completed sibling is untouched."""
    env = _setup_segmented_harness(monkeypatch, unit_count=18, root_part_target=2)
    assert len(env.db.segments) >= 2
    first_root_index = env.db.segments[0].segment_index
    second_root_index = env.db.segments[1].segment_index
    called_scopes: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    class TruncateSecondRootChat:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, messages: list[ChatMessage], request: ChatRequest):
            self.calls += 1
            incoming = json.loads(messages[-1].content)
            owned_s = tuple(u["id"] for u in incoming["source_units"])
            owned_d = tuple(u["id"] for u in incoming["draft_units"])
            called_scopes.append((owned_s, owned_d))
            seg_2_scope = env.db.segments[1].scope
            if (
                list(owned_s) == seg_2_scope["source_ids"]
                and list(owned_d) == seg_2_scope["draft_ids"]
            ):
                raise _truncation_error(usage_tokens=4096)
            content = _valid_assessment_json(incoming)
            return ChatResult(
                content=content,
                provider="openai-compatible",
                model=request.model,
                prompt_tokens=200,
                completion_tokens=120,
                finish_reason="stop",
                total_tokens=320,
                raw_body=json.dumps(
                    {
                        "choices": [{"message": {"content": content}}],
                        "usage": {"total_tokens": 320},
                    }
                ).encode("utf-8"),
            )

    chat = TruncateSecondRootChat()
    result = asyncio.run(
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
    assert result.status == "completed"
    first_root_scope = (
        tuple(env.db.segments[0].scope["source_ids"]),
        tuple(env.db.segments[0].scope["draft_ids"]),
    )
    assert called_scopes.count(first_root_scope) == 1

    second_root = env.db.segments[1]
    assert second_root.config.get("refined") is True
    assert second_root.config.get("refined_reason") == "chat_output_truncated"
    assert second_root.config.get("refined_usage_tokens") == 4096
    children = [s for s in env.db.segments if s.parent_segment_id == second_root.id]
    assert len(children) == 2
    assert all(child.status == "completed" for child in children)
    assert all(refinement.segment_depth(child) == 1 for child in children)
    refinement.verify_parent_child_coverage(env.db.segments)

    raw_parent = next(
        a
        for a in env.db.segment_artifacts
        if a.segment_id == second_root.id and a.kind == "raw_response"
    )
    assert b'"finish_reason": "length"' in env.blob.objects[raw_parent.blob_key]
    for seg in env.db.segments:
        assert any(
            a.segment_id == seg.id and a.kind == "assessment_json"
            for a in env.db.segment_artifacts
        )
        assert any(
            a.segment_id == seg.id and a.kind == "markdown"
            for a in env.db.segment_artifacts
        )

    expected_tokens = 4096 + 320 * len(refinement.ordered_leaves(env.db.segments))
    assert env.review.usage_tokens == expected_tokens
    assert first_root_index == 1 and second_root_index == 2


def test_retry_and_resume_do_not_create_duplicate_nodes_or_rerun_completed_parts(
    monkeypatch,
):
    """Batch 2 (2, 4): Resuming after mid-run truncation refines only the truncated leaf and skips completed leaves."""
    env = _setup_segmented_harness(monkeypatch, unit_count=18, root_part_target=2)
    seg1, seg2 = env.db.segments[0], env.db.segments[1]
    p1 = parts.plan_from_scope(seg1.scope)
    p1_payload = parts.payload_for(
        env.material.payload,
        p1.source_ids,
        p1.draft_ids,
        p1.context_source_ids,
        p1.context_draft_ids,
    )
    seg1_json = _valid_assessment_json(p1_payload).encode("utf-8")
    asyncio.run(
        artifacts.store_segment(
            env.db, env.blob, env.review, seg1, "assessment_json", seg1_json
        )
    )
    seg1.status = "completed"
    seg1.attempt_count = 1
    seg1.usage_tokens = 250
    seg1.finished_at = utcnow()

    seg2.status = "failed"
    seg2.error_code = "chat_output_truncated"
    seg2.attempt_count = 1
    seg2.usage_tokens = None  # Unknown usage on truncated request -> must remain None!
    seg2.finished_at = utcnow()

    for extra in env.db.segments[2:]:
        extra_p = parts.plan_from_scope(extra.scope)
        extra_payload = parts.payload_for(
            env.material.payload,
            extra_p.source_ids,
            extra_p.draft_ids,
            extra_p.context_source_ids,
            extra_p.context_draft_ids,
        )
        asyncio.run(
            artifacts.store_segment(
                env.db,
                env.blob,
                env.review,
                extra,
                "assessment_json",
                _valid_assessment_json(extra_payload).encode("utf-8"),
            )
        )
        extra.status = "completed"
        extra.attempt_count = 1
        extra.usage_tokens = 200
        extra.finished_at = utcnow()

    class ChildOnlyChat:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, messages: list[ChatMessage], request: ChatRequest):
            self.calls += 1
            incoming = json.loads(messages[-1].content)
            content = _valid_assessment_json(incoming)
            return ChatResult(
                content=content,
                provider="openai-compatible",
                model=request.model,
                prompt_tokens=100,
                completion_tokens=80,
                finish_reason="stop",
                total_tokens=180,
                raw_body=b'{"choices":[]}',
            )

    chat = ChildOnlyChat()
    result = asyncio.run(
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
    assert result.status == "completed"
    assert chat.calls == 2
    assert seg1.attempt_count == 1
    children = [s for s in env.db.segments if s.parent_segment_id == seg2.id]
    assert len(children) == 2
    assert env.review.usage_tokens is None


@pytest.mark.parametrize(
    ("policy", "expected_code"),
    [
        ({"max_depth": 0}, "compilation_review_refinement_depth_exceeded"),
        ({"max_nodes": 2}, "compilation_review_refinement_node_limit_exceeded"),
        ({"max_requests": 2}, "compilation_review_refinement_request_limit_exceeded"),
        # Token and time ceilings are enforced before every provider request, so they now
        # stop the first send instead of waiting for a node to need splitting.
        ({"max_tokens": 1000}, "compilation_review_budget_tokens_exceeded"),
        ({"max_seconds": 1}, "compilation_review_budget_time_exceeded"),
    ],
)
def test_refinement_limits_stop_deterministically(monkeypatch, policy, expected_code):
    """Batch 2 (5): Exceeding depth, node, request, token, or time limits stops with explicit code."""
    env = _setup_segmented_harness(
        monkeypatch, unit_count=18, root_part_target=2, refinement_policy=policy
    )
    if "max_seconds" in policy:
        env.review.created_at = utcnow() - timedelta(seconds=10)

    class AlwaysTruncateChat:
        async def complete(self, messages: list[ChatMessage], request: ChatRequest):
            raise _truncation_error(usage_tokens=900)

    with pytest.raises(AppException) as caught:
        asyncio.run(
            execution._execute_segments(
                env.db,
                env.blob,
                AlwaysTruncateChat(),
                env.actor,
                env.run.workspace_id,
                env.run,
                env.review,
                env.material,
                env.runtime,
            )
        )
    assert caught.value.code == expected_code
    assert env.review.status == "failed"
    assert env.review.error_code == expected_code


def test_atomic_limit_and_non_progress_stop_clearly():
    """Batch 2 (6): An atomic 1-unit segment cannot be split further and raises atomic_limit; non-progress raises no_progress."""
    payload = _build_material_payload(unit_count=1)
    single_plan = parts.build_part(
        payload,
        index=1,
        total=1,
        source_ids=[],
        draft_ids=["title"],
        context_source_ids=[],
        context_draft_ids=[],
        structured=False,
    )
    atomic_seg = CompilationReviewSegment(
        id="rvs_atomic",
        review_id="rvw_atomic",
        segment_index=1,
        status="failed",
        error_code="chat_output_truncated",
        scope=single_plan.scope_dict(),
        input_sha256=single_plan.input_sha256,
        prompt_version=parts.SEGMENT_PROMPT_VERSION,
        schema_sha256=single_plan.schema_sha256,
        config={"max_output_tokens": 4096},
        request_hash="req_atomic",
    )
    with pytest.raises(AppException) as caught:
        refinement.split_segment_plans(payload, atomic_seg, next_index=2, total_estimate=2)
    assert caught.value.code == "compilation_review_refinement_atomic_limit"

    with pytest.raises(AppException) as no_prog:
        refinement.assert_progress([], ["title"], (single_plan, single_plan))
    assert no_prog.value.code == "compilation_review_refinement_no_progress"


def test_timeout_and_uncertain_never_trigger_refinement_or_blind_resend(monkeypatch):
    """Batch 2 (7): Provider timeout/uncertain keeps segment uncertain and never splits or resends."""
    env = _setup_segmented_harness(monkeypatch, unit_count=18, root_part_target=2)

    class TimeoutChat:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, messages: list[ChatMessage], request: ChatRequest):
            self.calls += 1
            raise AppException(
                "Không xác định được kết quả từ provider.",
                code="chat_provider_uncertain",
                status_code=504,
            )

    chat = TimeoutChat()
    with pytest.raises(AppException) as caught:
        asyncio.run(
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
    assert caught.value.code == "chat_provider_uncertain"
    assert chat.calls == 1
    assert env.review.status == "uncertain"
    assert env.db.segments[0].status == "uncertain"
    assert all(seg.parent_segment_id is None for seg in env.db.segments)
    assert env.settled_records[0]["record"].total_tokens is None
    assert env.settled_records[0]["record"].status == "unknown"


def test_fencing_and_config_change_prevent_stale_commit_while_keeping_usage(monkeypatch):
    """Batch 2 (8, 9): Losing execution_token fence or changing provider config during call blocks commit but keeps usage."""
    env = _setup_segmented_harness(monkeypatch, unit_count=18, root_part_target=2)

    class StaleWorkerChat:
        async def complete(self, messages: list[ChatMessage], request: ChatRequest):
            env.review.trace = {**env.review.trace, "execution_token": "rex_new_owner"}
            content = _valid_assessment_json(json.loads(messages[-1].content))
            return ChatResult(
                content=content,
                provider="openai-compatible",
                model=request.model,
                prompt_tokens=210,
                completion_tokens=200,
                finish_reason="stop",
                total_tokens=410,
                raw_body=b'{"choices":[{"message":{"content":"{}"}}]}',
            )

    with pytest.raises(AppException) as caught:
        asyncio.run(
            execution._execute_segments(
                env.db,
                env.blob,
                StaleWorkerChat(),
                env.actor,
                env.run.workspace_id,
                env.run,
                env.review,
                env.material,
                env.runtime,
            )
        )
    assert caught.value.code == "compilation_review_claim_lost"
    seg = env.db.segments[0]
    assert seg.status != "completed"
    assert seg.usage_tokens == 410
    assert env.settled_records[0]["record"].total_tokens == 410
    assert any(
        a.segment_id == seg.id and a.kind == "raw_response"
        for a in env.db.segment_artifacts
    )
    assert not any(
        a.segment_id == seg.id and a.kind == "assessment_json"
        for a in env.db.segment_artifacts
    )


def test_reducer_rejects_incomplete_leaves_or_parent_coverage_mismatch(monkeypatch):
    """Batch 3: Reducer refuses to merge when a leaf is incomplete or parent-child ownership mismatches."""
    env = _setup_segmented_harness(monkeypatch, unit_count=18, root_part_target=2)
    with pytest.raises(AppException) as incomplete:
        asyncio.run(
            execution._merged_assessments(
                env.db, env.blob, env.review, env.db.segments, env.material
            )
        )
    assert incomplete.value.code == "compilation_review_segment_incomplete"

    parent = env.db.segments[0]
    bad_child = CompilationReviewSegment(
        id="rvs_bad_child",
        review_id=env.review.id,
        parent_segment_id=parent.id,
        segment_index=99,
        status="completed",
        scope={**parent.scope, "source_ids": []},
        input_sha256="bad",
        prompt_version=parts.SEGMENT_PROMPT_VERSION,
        schema_sha256="bad",
        config={},
        request_hash="bad",
    )
    with pytest.raises(AppException) as mismatch:
        refinement.verify_parent_child_coverage([parent, bad_child])
    assert mismatch.value.code == "compilation_review_plan_invalid"
