import pytest

from qnu.domains.knowledge.compilation.execution import _optional_ai_failure
from qnu.domains.knowledge.compilation.schemas import CompilationRequest
from qnu.domains.knowledge.compilation.supplement import select_units


def test_only_contiguous_unheaded_prose_is_selected():
    paragraphs = [
        {"evidence_id": str(index), "text": text, "type": "text"}
        for index, text in enumerate(
            [
                "Nội dung đầu tiên giải thích rõ cách bộ phận thực hiện công việc mỗi tuần.",
                "Các nhân sự liên quan sẽ cùng đối chiếu và lưu lại thông tin theo ngày.",
                "Phần I. Kế hoạch",
                "Kế hoạch tổng hợp công việc theo tháng được gửi cho đơn vị theo quy định.",
            ],
            start=1,
        )
    ]
    document = {"ocr_run_id": "sample", "pages": [{"page_number": 1, "blocks": paragraphs}]}
    assert [unit.evidence_id for unit in select_units([document])] == ["1", "2"]


@pytest.mark.parametrize(
    "code",
    [
        "compilation_refinement_atomic_limit",
        "compilation_refinement_depth_exhausted",
        "compilation_refinement_nodes_exhausted",
        "chat_provider_uncertain",
        "compilation_draft_invalid",
    ],
)
def test_optional_inference_failures_keep_the_source_draft(code):
    assert _optional_ai_failure(code)


@pytest.mark.parametrize(
    "code",
    [
        "compilation_source_mismatch",
        "compilation_segment_manifest_mismatch",
        "compilation_refinement_scope_invalid",
        "storage_read_failed",
        "chat_provider_changed",
        "model_token_limits_stale",
        "model_token_limits_invalid",
        "model_connection_mismatch",
        "model_mismatch",
    ],
)
def test_source_integrity_errors_are_still_fatal(code):
    assert not _optional_ai_failure(code)


@pytest.mark.parametrize("legacy_mode", ["source_first", "ai_supplement"])
def test_new_mode_cannot_be_combined_with_legacy_modes(legacy_mode):
    with pytest.raises(ValueError, match="Chọn một chế độ"):
        CompilationRequest(
            topic="Tài liệu",
            ocr_run_ids=["source"],
            selective_supplement=True,
            **{legacy_mode: True},
        )
