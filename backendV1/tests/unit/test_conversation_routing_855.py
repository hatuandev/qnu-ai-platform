import json

import pytest
from pydantic import ValidationError

from qnu.domains.conversations.routing import RoutedTurn, messages_for


def test_router_messages_keep_user_input_as_data_and_only_include_public_identity():
    question = "Xin chào, cho biết điều kiện nhập học?"
    messages = messages_for(
        question,
        ["Câu hỏi trước"],
        {"name": "Trợ lý học vụ", "persona": "Xưng mình, gọi bạn.", "api_key": "not-for-model"},
    )
    assert [m.role for m in messages] == ["system", "user"]
    assert "Trợ lý học vụ" in messages[0].content
    assert "Xưng mình, gọi bạn." in messages[0].content
    assert question not in messages[0].content and "not-for-model" not in messages[0].content
    assert json.loads(messages[1].content) == {
        "current_question": question,
        "previous_user_questions": ["Câu hỏi trước"],
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"route": "unknown"},
        {"answer": "Tự trả lời dữ kiện trước khi tìm nguồn"},
        {"standalone_question": "   "},
        {"route": "greeting", "answer": None},
        {"route": "greeting", "answer": "   "},
        {"route": "identity", "answer": "Lời đáp", "needs_clarification": True},
    ],
)
def test_invalid_router_output_does_not_become_an_answer(changes):
    with pytest.raises(ValidationError):
        RoutedTurn.model_validate(
            {
                "route": "knowledge",
                "answer": None,
                "standalone_question": "Điều kiện nào?",
                "needs_clarification": False,
                **changes,
            }
        )
