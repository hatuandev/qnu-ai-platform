"""Unit tests for Multi-Pass Async OCR spelling check and publication gates."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.publication import decisions
from qnu.domains.knowledge.publication.schemas import PreviewRequest
from qnu.domains.modelops.capacity.schemas import ModelTokenLimits, RequestTokenBudget
from qnu.domains.modelops.document_processing import DocumentGroup, GroupModel
from qnu.domains.modelops.public_api import ChatRuntime
from qnu.domains.ocr.review import automatic, defaults, detection
from qnu.domains.ocr.review.models import SpellingDisposition, SpellingRun
from qnu.domains.ocr.review.schemas import DetectionResponse, IgnoredSuggestion, Suggestion
from qnu.platform.errors import Conflict


@pytest.mark.asyncio
async def test_multi_pass_disposition_inheritance():
    """Ignored suggestions in parent pass are automatically inherited by child pass."""
    db = AsyncMock()

    # db.execute for parent_run_ids query
    execute_result = MagicMock()
    execute_result.all.return_value = [("child_run_1", "parent_run_1")]
    db.execute.return_value = execute_result

    # db.scalars for SpellingDisposition query
    disp_parent = SpellingDisposition(
        id="d1",
        check_id="parent_run_1",
        evidence_id="ev_01",
        span_start=10,
        span_end=20,
    )
    disp_child = SpellingDisposition(
        id="d2",
        check_id="child_run_1",
        evidence_id="ev_02",
        span_start=30,
        span_end=40,
    )
    scalars_result = MagicMock()
    scalars_result.all.return_value = [disp_parent, disp_child]
    db.scalars.return_value = scalars_result

    ignored_map = await detection.ignored_suggestions(db, ["child_run_1"])

    assert "child_run_1" in ignored_map
    items = ignored_map["child_run_1"]
    spans = {(it.evidence_id, it.start, it.end) for it in items}
    # Both parent and child dispositions must be present in child's ignored set
    assert ("ev_01", 10, 20) in spans
    assert ("ev_02", 30, 40) in spans


@pytest.mark.asyncio
async def test_multi_pass_aggregate_merges_and_deduplicates():
    """Pass 2 aggregate merges suggestions from Pass 1, removes duplicates and ignored spans."""
    db = AsyncMock()

    parent_pass1 = SpellingRun(
        id="pass1_id",
        canonical_sha256="hash_abc",
        suggestions=[
            {
                "evidence_id": "ev_01",
                "start": 0,
                "end": 5,
                "original": "toa nha",
                "replacement": "tòa nhà",
                "reason": "Lỗi dấu",
                "pass_number": 1,
            },
            {
                "evidence_id": "ev_02",
                "start": 10,
                "end": 15,
                "original": "chu ky",
                "replacement": "chữ ký",
                "reason": "Lỗi dấu",
                "pass_number": 1,
            },
            {
                "evidence_id": "ev_ign",
                "start": 0,
                "end": 3,
                "original": "qnu",
                "replacement": "QNU",
                "reason": "Viết hoa tên viết tắt",
                "pass_number": 1,
            },
        ],
    )
    db.get.return_value = parent_pass1

    current_pass2 = SpellingRun(
        id="pass2_id",
        pass_number=2,
        parent_run_id="pass1_id",
        canonical_sha256="hash_abc",
        checked_evidence_ids=[],
        suggestions=[],
        trace={},
    )

    positions = {"ev_01": 0, "ev_02": 1, "ev_03": 2, "ev_ign": 3}

    now = datetime.now(UTC)
    # Pass 2 detection returns:
    # 1. Duplicate of ev_02 span (10, 15)
    # 2. Re-occurrence of ignored span (ev_ign, 0, 3)
    # 3. New suggestion on ev_03
    raw_results = [
        DetectionResponse(
            id="det_1",
            status="completed",
            version=0,
            canonical_sha256="hash_abc",
            checked_evidence_ids=["ev_02", "ev_03", "ev_ign"],
            suggestions=[
                Suggestion(
                    evidence_id="ev_02",
                    start=10,
                    end=15,
                    original="chu ky",
                    replacement="chữ ký",
                    reason="Lỗi dấu",
                ),
                Suggestion(
                    evidence_id="ev_ign",
                    start=0,
                    end=3,
                    original="qnu",
                    replacement="QNU",
                    reason="Viết hoa tên viết tắt",
                ),
                Suggestion(
                    evidence_id="ev_03",
                    start=20,
                    end=30,
                    original="chuong trinh",
                    replacement="chương trình",
                    reason="Thiếu dấu tiếng Việt",
                ),
            ],
            withheld_suggestions=[],
            rejected_suggestions=[],
            error_code=None,
            usage_id=None,
            created_at=now,
        )
    ]

    with patch(
        "qnu.domains.ocr.review.detection.ignored_suggestions",
        return_value={"pass1_id": [IgnoredSuggestion(evidence_id="ev_ign", start=0, end=3)]},
    ):
        await automatic._aggregate(db, current_pass2, raw_results, positions)

    # Ignored span must be excluded
    s_keys = [(s["evidence_id"], s["start"], s["end"]) for s in current_pass2.suggestions]
    assert ("ev_ign", 0, 3) not in s_keys

    # Must contain ev_01 (from pass 1), ev_02 (from pass 1, not duplicated), and ev_03 (new in pass 2)
    assert ("ev_01", 0, 5) in s_keys
    assert ("ev_02", 10, 15) in s_keys
    assert ("ev_03", 20, 30) in s_keys
    assert len(current_pass2.suggestions) == 3

    # Check pass numbers
    pass_map = {s["evidence_id"]: s.get("pass_number") for s in current_pass2.suggestions}
    assert pass_map["ev_01"] == 1
    assert pass_map["ev_02"] == 1
    assert pass_map["ev_03"] == 2


@pytest.mark.asyncio
async def test_multi_pass_stops_on_hash_mismatch():
    """Pass k stops early with hash_mismatch_stopped if text was modified since parent pass."""
    db = AsyncMock()
    db.add = MagicMock()
    blob = AsyncMock()
    chat = AsyncMock()
    actor = AuthActor(
        actor_type="user",
        actor_id="user_1",
        username="test_user",
        system_role="admin",
        permissions=frozenset(),
        active_role="admin",
    )
    run = SimpleNamespace(
        id="ocr_run_1",
        workspace_id="ws_1",
        collection_id="col_1",
        source_id="src_1",
        revision_id="rev_1",
    )

    doc = SimpleNamespace(version=0, canonical_sha256="new_hash_modified", units=[])
    parent_pass1 = SpellingRun(
        id="pass1_id",
        canonical_sha256="old_hash_original",
    )
    db.get.return_value = parent_pass1

    with (
        patch("qnu.domains.ocr.review.service.authorize", return_value=None),
        patch("qnu.domains.ocr.review.service.load_review", return_value=(doc, {})),
    ):
        status, check_id = await automatic.review_document(
            db,
            blob,
            chat,
            actor,
            run,
            version=0,
            pass_number=2,
            parent_run_id="pass1_id",
        )

    assert status == "hash_mismatch_stopped"
    assert check_id is None


@pytest.mark.asyncio
async def test_spelling_reconcile_recovers_missing_passes():
    """Reconcile discovers missing Pass 1 and missing Pass 2 jobs."""
    from qnu.workers.tasks import ocr

    db = AsyncMock()
    container = SimpleNamespace(job_queue=AsyncMock())
    container.job_queue.enqueue.return_value = True

    # 1. Pass 1 missing: 1 OCR run finished without any spelling run
    # 2. Pass 2 missing: 1 SpellingRun completed at Pass 1, total_passes=2, but no Pass 2 exists
    scalars_mock = MagicMock()
    # First call for pass1_missing, second call for pass1_completed
    scalars_mock.all.side_effect = [
        ["ocr_run_without_pass1"],
        [
            SpellingRun(
                id="pass1_run_id",
                run_id="ocr_run_with_pass1_only",
                version=0,
                pass_number=1,
                total_passes=2,
                canonical_sha256="hash_123",
                batch_group_id="bg_123",
            )
        ],
    ]
    db.scalars.return_value = scalars_mock

    # db.scalar for has_pass2 check returns None (no pass 2 found)
    db.scalar.return_value = None

    context = {"container": container}
    with patch("qnu.workers.tasks.ocr.AsyncSessionFactory") as session_maker:
        session_maker.return_value.__aenter__.return_value = db
        requeued = await ocr.spelling_reconcile(context)

    assert requeued == 2
    assert container.job_queue.enqueue.call_count == 2

    # Check Pass 1 enqueue args
    call_p1 = container.job_queue.enqueue.call_args_list[0]
    assert call_p1.args[0] == "spelling_check_job"
    assert call_p1.args[1] == "ocr_run_without_pass1"
    assert call_p1.args[5] == 1  # pass_number = 1

    # Check Pass 2 enqueue args
    call_p2 = container.job_queue.enqueue.call_args_list[1]
    assert call_p2.args[0] == "spelling_check_job"
    assert call_p2.args[1] == "ocr_run_with_pass1_only"
    assert call_p2.args[5] == 2  # pass_number = 2
    assert call_p2.args[6] == "pass1_run_id"  # parent_run_id
    assert call_p2.args[7] == "bg_123"  # batch_group_id


@pytest.mark.asyncio
async def test_publication_gate_blocks_and_allows_with_confirmation():
    """Publication review gate blocks when multi-pass is in progress, unless explicitly confirmed."""
    db = AsyncMock()
    db.add = MagicMock()
    blob = AsyncMock()
    actor = AuthActor(
        actor_type="user",
        actor_id="approver_1",
        username="approver",
        system_role="admin",
        permissions=frozenset(),
        active_role="admin",
    )

    doc = SimpleNamespace(id="doc_1", status="approved", change_sequence=1)
    target_version = SimpleNamespace(
        id="ver_1",
        status="compiled",
        compilation_run_id="comp_1",
        bundle_sha256="a" * 64,
        state_version=1,
    )

    with (
        patch("qnu.domains.knowledge.publication.decisions.authorize", return_value=None),
        patch("qnu.domains.knowledge.publication.decisions.document", return_value=doc),
        patch("qnu.domains.knowledge.publication.decisions.version", return_value=target_version),
        patch("qnu.domains.knowledge.publication.decisions.transition", return_value=None),
        patch(
            "qnu.domains.knowledge.publication.review_gate.material",
            return_value={
                "review_id": "rev_gate_1",
                "spelling_in_progress": True,
                "spelling_details": {
                    "pass_number": 2,
                    "total_passes": 2,
                    "pass_name": "context_terminology",
                    "check_id": "sp_chk_2",
                },
            },
        ),
        patch(
            "qnu.domains.knowledge.publication.review_gate.acknowledge",
            return_value={"confirmed_reviewed": True},
        ),
        patch(
            "qnu.domains.knowledge.publication.decisions.load_bundle",
            return_value=SimpleNamespace(target=target_version, manifest={}),
        ),
        patch("qnu.domains.knowledge.publication.decisions.assert_pinned", return_value=None),
        patch("qnu.domains.knowledge.publication.decisions.active_version", return_value=None),
    ):
        # 1. Without confirmation -> Conflict (publication_spelling_in_progress)
        req_unconfirmed = PreviewRequest(
            action="approve",
            reason="Ready to approve",
            confirm_spelling_in_progress=False,
            review_ack={
                "review_id": "rev_gate_1",
                "report_sha256": "0" * 64,
                "confirmed_reviewed": True,
            },
        )
        with pytest.raises(Conflict) as exc_info:
            await decisions.create_preview(
                db,
                blob,
                actor,
                "ws_1",
                "col_1",
                "doc_1",
                "ver_1",
                req_unconfirmed,
            )
        assert exc_info.value.code == "publication_spelling_in_progress"
        assert "Lượt 2/2: context_terminology" in str(exc_info.value)

        # 2. With confirmation -> passes gate
        req_confirmed = PreviewRequest(
            action="approve",
            reason="Approving despite spelling in progress",
            confirm_spelling_in_progress=True,
            review_ack={
                "review_id": "rev_gate_1",
                "report_sha256": "0" * 64,
                "confirmed_reviewed": True,
            },
        )
        preview = await decisions.create_preview(
            db,
            blob,
            actor,
            "ws_1",
            "col_1",
            "doc_1",
            "ver_1",
            req_confirmed,
        )
        assert preview.version_id == "ver_1"
        assert preview.action == "approve"
        assert preview.review_ack == {"confirmed_reviewed": True}


def test_spelling_defaults_total_passes_validation():
    """total_passes must be between 1 and 4."""
    for valid in (1, 2, 3, 4):
        policy = defaults.SpellingDefaults(total_passes=valid)
        assert policy.total_passes == valid

    for invalid in (0, 5, -1, 10):
        with pytest.raises(ValidationError):
            defaults.SpellingDefaults(total_passes=invalid)


def test_plan_batches_with_integer_min_available_envelope():
    """plan_batches accepts an int limits representing minimum available tokens across models."""
    from qnu.domains.ocr.review.schemas import TextUnit

    rows = {
        f"ev_{i:02d}": TextUnit(
            evidence_id=f"ev_{i:02d}",
            page=1,
            kind="paragraph",
            text="Nội dung văn bản dài mẫu để tính dung lượng batch " * 10,
            original_text="",
            bbox={},
        )
        for i in range(10)
    }
    canonical = {
        "pages": [
            {
                "page_number": 1,
                "blocks": [{"evidence_id": k, "type": "paragraph", "text": u.text} for k, u in rows.items()],
            }
        ]
    }
    # Tight integer budget: only a few units fit per batch
    batches = automatic.plan_batches(
        list(rows),
        rows,
        canonical,
        0,
        "a" * 64,
        limits=400,
        output_tokens=100,
    )
    assert len(batches) > 1
    total_planned = sum(len(group) for _, group in batches)
    assert total_planned == 10


@pytest.mark.asyncio
async def test_automatic_review_document_uses_document_group_models():
    """review_document pins models from document_processing instead of chatbot default."""
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.return_value = None
    blob = AsyncMock()
    chat = AsyncMock()
    actor = AuthActor(
        actor_type="user",
        actor_id="user_1",
        username="test_user",
        system_role="admin",
        permissions=frozenset(),
        active_role="admin",
    )
    run = SimpleNamespace(
        id="ocr_run_1",
        workspace_id="ws_1",
        collection_id="col_1",
        source_id="src_1",
        revision_id="rev_1",
    )
    unit = SimpleNamespace(evidence_id="ev_01", text="Nội dung kiểm tra")
    doc = SimpleNamespace(version=0, canonical_sha256="hash_doc", units=[unit])

    mock_group = DocumentGroup(
        mode="priority",
        models=(GroupModel("doc_model_custom", 2),),
    )

    mock_runtime = MagicMock(spec=ChatRuntime)
    mock_runtime.provider_id = "doc_model_custom"
    mock_runtime.model_name = "custom-llm"
    mock_runtime.token_limits = ModelTokenLimits(context_window_tokens=32768, max_output_tokens=4096)
    mock_runtime.routing_trace = ()
    mock_runtime.inference_configuration_hash.return_value = "cfg_custom"

    mock_budget = RequestTokenBudget(
        input_tokens=100,
        reserve_tokens=4096,
        max_output_tokens=4096,
        total_reserved_tokens=4196,
    )

    with (
        patch("qnu.domains.ocr.review.service.authorize", return_value=None),
        patch("qnu.domains.ocr.review.service.load_review", return_value=(doc, {"pages": [{"page_number": 1, "blocks": [{"evidence_id": "ev_01", "type": "paragraph", "text": "abc", "bbox": {}}]}]})),
        patch("qnu.domains.ocr.review.automatic.resolve_revision_scope", return_value=SimpleNamespace(extension=".pdf")),
        patch("qnu.domains.ocr.review.defaults.read", return_value=defaults.SpellingDefaults(ocr=True, pdf_text=True, word_text=True, total_passes=2)),
        patch("qnu.domains.ocr.review.automatic.resolve_document_group", return_value=mock_group),
        patch("qnu.domains.ocr.review.automatic.prepare_chat_limits", return_value=(mock_runtime, mock_budget)) as prep_mock,
        patch("qnu.domains.ocr.review.automatic._resume_results", return_value=[]),
        patch("qnu.domains.ocr.review.detection.check_running", return_value=SpellingRun(id="spl_new", canonical_sha256="hash_doc", trace={})),
        patch("qnu.domains.ocr.review.automatic._aggregate", return_value=None),
        patch("qnu.domains.ocr.review.automatic._review_batches", return_value=("completed", "spl_new")),
    ):
        status, check_id = await automatic.review_document(
            db,
            blob,
            chat,
            actor,
            run,
            version=0,
            automatic=True,
            pass_number=1,
            total_passes=2,
        )

    assert status == "completed"
    assert check_id == "spl_new"
    # Proves document_processing model was pinned instead of chat default
    prep_mock.assert_called_once()
    assert prep_mock.call_args.kwargs["provider_id"] == "doc_model_custom"


@pytest.mark.asyncio
async def test_review_batches_parallel_work_stealing_and_provider_attribution():
    """_review_batches distributes batches across slots via work-stealing and tags provider_id."""
    db = AsyncMock()
    blob = AsyncMock()
    chat = AsyncMock()
    actor = AuthActor(
        actor_type="user",
        actor_id="user_1",
        username="test_user",
        system_role="admin",
        permissions=frozenset(),
        active_role="admin",
    )

    doc = SimpleNamespace(version=0, canonical_sha256="hash_valid", units=[])
    index = MagicMock()

    runtime_fast = MagicMock()
    runtime_fast.provider_id = "provider_fast"
    slot_fast = automatic.SpellingSlot(
        provider_id="provider_fast",
        concurrency=2,
        runtime=runtime_fast,
        budget=MagicMock(),
        configuration_hash="cfg_fast",
    )

    runtime_slow = MagicMock()
    runtime_slow.provider_id = "provider_slow"
    slot_slow = automatic.SpellingSlot(
        provider_id="provider_slow",
        concurrency=1,
        runtime=runtime_slow,
        budget=MagicMock(),
        configuration_hash="cfg_slow",
    )

    batches = [(0, ["ev_1"]), (1, ["ev_2"]), (2, ["ev_3"])]
    positions = {"ev_1": 0, "ev_2": 1, "ev_3": 2}

    parent = SpellingRun(
        id="parent_chk_1",
        canonical_sha256="hash_valid",
        status="running",
        pass_number=1,
        total_passes=2,
        checked_evidence_ids=[],
        suggestions=[],
        trace={},
    )

    now = datetime.now(UTC)

    async def fake_inspect(*args, **kwargs):
        group = kwargs.get("group") or args[10]
        runtime_arg = kwargs.get("runtime") or args[6]
        return DetectionResponse(
            id=f"det_{group[0]}",
            status="completed",
            version=0,
            canonical_sha256="hash_valid",
            checked_evidence_ids=group,
            suggestions=[
                Suggestion(
                    evidence_id=group[0],
                    start=0,
                    end=3,
                    original="abc",
                    replacement="ABC",
                    reason="Viết hoa",
                    provider_id=runtime_arg.provider_id,
                )
            ],
            withheld_suggestions=[],
            rejected_suggestions=[],
            error_code=None,
            usage_id=None,
            created_at=now,
        )

    with (
        patch("qnu.domains.ocr.review.detection.check_running", return_value=parent),
        patch("qnu.domains.ocr.review.automatic._inspect_batch", side_effect=fake_inspect),
        patch("qnu.domains.ocr.review.automatic._finish", return_value=("completed", "parent_chk_1")),
    ):
        status, check_id = await automatic._review_batches(
            db,
            blob,
            chat,
            actor,
            "run_1",
            doc,
            index,
            [slot_fast, slot_slow],
            "parent_chk_1",
            batches,
            [],
            positions,
            pass_number=1,
            total_passes=2,
        )

    assert status == "completed"
    assert check_id == "parent_chk_1"
    assert len(parent.suggestions) == 3
    # Every suggestion has provider_id tagged
    for s in parent.suggestions:
        assert s["provider_id"] in {"provider_fast", "provider_slow"}

    # batch_providers recorded in trace
    assert "batch_providers" in parent.trace
    assert len(parent.trace["batch_providers"]) == 3
    assert set(parent.trace["used_providers"]).issubset({"provider_fast", "provider_slow"})


@pytest.mark.asyncio
async def test_review_batches_stops_on_hash_mismatch_during_execution():
    """_review_batches stops immediately with hash_mismatch_stopped if text was modified."""
    db = AsyncMock()
    blob = AsyncMock()
    chat = AsyncMock()
    actor = AuthActor(
        actor_type="user",
        actor_id="user_1",
        username="test_user",
        system_role="admin",
        permissions=frozenset(),
        active_role="admin",
    )

    doc = SimpleNamespace(version=0, canonical_sha256="hash_new_modified", units=[])
    index = MagicMock()

    slot = automatic.SpellingSlot(
        provider_id="provider_1",
        concurrency=1,
        runtime=MagicMock(),
        budget=MagicMock(),
        configuration_hash="cfg_1",
    )

    batches = [(0, ["ev_1"])]
    positions = {"ev_1": 0}

    # parent in DB has old hash
    parent_old = SpellingRun(
        id="parent_chk_old",
        canonical_sha256="hash_old_stale",
        status="running",
        pass_number=1,
        total_passes=2,
        checked_evidence_ids=[],
        suggestions=[],
        trace={},
    )

    with (
        patch("qnu.domains.ocr.review.detection.check_running", return_value=parent_old),
        patch("qnu.domains.ocr.review.automatic._finish", return_value=("hash_mismatch_stopped", "parent_chk_old")),
    ):
        status, _check_id = await automatic._review_batches(
            db,
            blob,
            chat,
            actor,
            "run_1",
            doc,
            index,
            [slot],
            "parent_chk_old",
            batches,
            [],
            positions,
        )

    assert status == "hash_mismatch_stopped"


@pytest.mark.asyncio
async def test_settings_spelling_endpoint_read_and_save():
    """Test get_defaults and update_defaults handlers directly."""
    from qnu.domains.ocr.review import defaults_router

    db = AsyncMock()
    # Mock defaults.read
    with patch(
        "qnu.domains.ocr.review.defaults_router.read",
        return_value=defaults.SpellingDefaults(ocr=True, pdf_text=False, word_text=True, total_passes=3),
    ):
        res = await defaults_router.get_defaults(db)
        assert res.total_passes == 3
        assert res.word_text is True

    # Mock defaults.save
    req = defaults.SpellingDefaults(ocr=False, pdf_text=True, word_text=False, total_passes=4)
    with patch("qnu.domains.ocr.review.defaults_router.save", return_value=req):
        saved = await defaults_router.update_defaults(req, db)
        assert saved.total_passes == 4
        assert saved.pdf_text is True


