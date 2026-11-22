"""Unit tests for promoting conversation turns to the RAG benchmark suite."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qnu.domains.conversations.benchmarks import (
    _normalize_question,
    add_turn_to_benchmark,
    is_question_in_benchmark,
)
from qnu.domains.conversations.history import promote_turn_to_benchmark
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.conversations.schemas import PromoteToBenchmarkRequest
from qnu.domains.identity.actor import AuthActor
from qnu.platform.errors import EntityNotFound


def test_normalize_question():
    q1 = "   Thời gian đào tạo   tiêu chuẩn?   "
    q2 = "Thời gian đào tạo tiêu chuẩn?"
    assert _normalize_question(q1) == _normalize_question(q2)
    assert _normalize_question("Quy định tín chỉ") == "quy định tín chỉ"


def test_is_question_in_benchmark():
    data = {
        "questions": [
            {"id": "Q01", "question": "Quy định này áp dụng từ năm nào?"},
            {"id": "Q02", "question": "Học bổng KKHT được xét như thế nào?"},
        ]
    }
    found, qid = is_question_in_benchmark(data, "  quy định này áp dụng từ năm nào?  ")
    assert found is True
    assert qid == "Q01"

    found, qid = is_question_in_benchmark(data, "Câu hỏi hoàn toàn mới?")
    assert found is False
    assert qid is None


def test_add_turn_to_benchmark_success_and_deduplication():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        bench_file = tmp_path / "test_benchmark.json"
        initial_data = {
            "suite_id": "test_suite",
            "scoring_scale": {
                "PASS": 2,
                "PARTIAL": 1,
                "FAIL": 0,
                "max_score_per_question": 2,
                "total_questions": 2,
                "max_total_score": 4,
            },
            "groups": [
                {"id": "general", "name": "Chung", "question_count": 2},
            ],
            "questions": [
                {"id": "Q01", "group": "general", "question": "Câu hỏi 1?"},
                {"id": "Q02", "group": "general", "question": "Câu hỏi 2?"},
            ],
        }
        bench_file.write_text(
            json.dumps(initial_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        fake_turn = MagicMock(spec=ConversationTurn)
        fake_turn.id = "turn_err_1"
        fake_turn.question = "Học phí ngành Sư phạm Toán năm 2025 là bao nhiêu?"
        fake_turn.status = "completed"
        fake_turn.error_code = None
        fake_turn.feedback = {
            "rating": "dislike",
            "reason": "Sai năm / mốc chu kỳ triển khai",
        }
        fake_turn.result = {
            "status": "answered",
            "sources": [{"source_title": "Quy_dinh_hoc_phi_2024.pdf"}],
        }

        # 1. Add for the first time
        res1 = add_turn_to_benchmark(bench_file, fake_turn)
        assert res1.already_exists is False
        assert res1.question_id == "Q03"
        assert res1.total_questions == 3

        # Check file content on disk
        updated_data = json.loads(bench_file.read_text(encoding="utf-8"))
        assert updated_data["scoring_scale"]["total_questions"] == 3
        assert updated_data["scoring_scale"]["max_total_score"] == 6
        assert len(updated_data["questions"]) == 3
        q3 = updated_data["questions"][-1]
        assert q3["id"] == "Q03"
        assert q3["group"] == "log_failures"
        assert q3["doc_scope"] == "Quy_dinh_hoc_phi_2024.pdf"
        assert "Sai năm / mốc chu kỳ triển khai" in q3["forbidden_behaviors"]

        # 2. Add same question again (with extra whitespace & lowercase)
        fake_turn_dup = MagicMock(spec=ConversationTurn)
        fake_turn_dup.id = "turn_err_2"
        fake_turn_dup.question = "  học phí ngành sư phạm toán năm 2025 là bao nhiêu?  "
        fake_turn_dup.status = "completed"
        fake_turn_dup.error_code = None
        fake_turn_dup.feedback = None
        fake_turn_dup.result = None

        res2 = add_turn_to_benchmark(bench_file, fake_turn_dup)
        assert res2.already_exists is True
        assert res2.question_id == "Q03"
        assert res2.total_questions == 3

        # File must still have 3 questions
        data_after_dup = json.loads(bench_file.read_text(encoding="utf-8"))
        assert len(data_after_dup["questions"]) == 3


@pytest.mark.asyncio
async def test_promote_turn_service_flow():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        bench_file = tmp_path / "test_benchmark.json"
        initial_data = {
            "suite_id": "test_suite",
            "questions": [{"id": "Q01", "question": "Câu 1"}],
        }
        bench_file.write_text(
            json.dumps(initial_data, ensure_ascii=False), encoding="utf-8"
        )

        fake_actor = AuthActor(
            actor_id="user_1",
            username="testuser",
            actor_type="user",
            roles=["member"],
            workspaces=["ws_test"],
        )
        fake_conv = MagicMock(spec=Conversation)
        fake_conv.id = "conv_1"

        fake_turn = MagicMock(spec=ConversationTurn)
        fake_turn.id = "turn_fail_1"
        fake_turn.question = (
            "Sinh viên được cảnh báo học tập bao nhiêu lần thì bị buộc thôi học?"
        )
        fake_turn.status = "failed"
        fake_turn.error_code = "conversation_turn_failed"
        fake_turn.feedback = None
        fake_turn.result = None

        db = AsyncMock()
        db.scalar.return_value = fake_turn

        with (
            patch(
                "qnu.domains.conversations.history.owned",
                new=AsyncMock(return_value=fake_conv),
            ),
            patch("qnu.domains.conversations.history.expire", new=AsyncMock()),
            patch(
                "qnu.domains.conversations.benchmarks.get_benchmark_path",
                return_value=bench_file,
            ),
        ):
            res = await promote_turn_to_benchmark(
                db,
                fake_actor,
                "ws_test",
                "conv_1",
                "turn_fail_1",
                PromoteToBenchmarkRequest(),
            )
            assert res.already_exists is False
            assert res.question_id == "Q02"
            assert res.total_questions == 2



@pytest.mark.asyncio
async def test_promote_turn_not_found():
    fake_actor = AuthActor(
        actor_id="user_1",
        username="testuser",
        actor_type="user",
        roles=["member"],
        workspaces=["ws_test"],
    )
    fake_conv = MagicMock(spec=Conversation)
    fake_conv.id = "conv_1"

    db = AsyncMock()
    db.scalar.return_value = None

    with (
        patch("qnu.domains.conversations.history.owned", new=AsyncMock(return_value=fake_conv)),
        patch("qnu.domains.conversations.history.expire", new=AsyncMock()),
    ):
        with pytest.raises(EntityNotFound) as exc_info:
            await promote_turn_to_benchmark(
                db,
                fake_actor,
                "ws_test",
                "conv_1",
                "nonexistent",
                PromoteToBenchmarkRequest(),
            )
        assert exc_info.value.code == "conversation_turn_not_found"
