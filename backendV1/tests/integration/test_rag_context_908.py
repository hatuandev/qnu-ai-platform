"""Real API/adapter boundaries for row narrowing and declared judge reasoning."""

import json

import pytest

from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ask
from tests.integration.test_answers_api_648 import ready as ready_fixture
from tests.integration.test_index_api_647 import indexed  # noqa: F401
from tests.integration.test_rag_verification_policy_672 import judging

ready = ready_fixture


@pytest.mark.parametrize("verified", [False, True])
def test_declared_reasoning_reaches_both_generation_and_judge(client, ready, verified):
    as_actor(PLATFORM)
    configured = client.put(
        f"{API}/modelops/providers/{ready['chat_provider']['id']}/reasoning",
        json={
            "policy": {
                "mode": "chat_template_kwarg",
                "parameter": "enable_thinking",
                "off_value": False,
                "tasks": {"off": ["answer"]},
                "verified": verified,
            }
        },
    )
    assert configured.status_code == 200, configured.text
    as_actor(EDITOR)
    judging(ready)
    response = ask(client, ready, verification_mode="observe")
    assert response.status_code == 200, response.text
    trace = response.json()["trace"]
    assert trace["verification"]["status"] == "supported"
    assert trace["reasoning"]["applied"] is verified
    assert trace["verification"]["reasoning"]["applied"] is verified
    assert (
        trace["verification"]["inference_configuration_hash"]
        == trace["inference_configuration_hash"]
    )
    requests = ready["answer_chat"].requests
    assert len(requests) == 2
    for request in requests:
        body = request["body"]
        if verified:
            assert body["chat_template_kwargs"] == {"enable_thinking": False}
        else:
            assert "chat_template_kwargs" not in body


def test_row_selection_does_not_supply_another_metric_to_the_model(client, ready):
    response = ask(client, ready, question="Chỉ tiêu tuyển sinh năm 2024 là bao nhiêu?")
    assert response.status_code == 200, response.text
    payload = json.loads(ready["answer_chat"].requests[0]["body"]["messages"][-1]["content"])
    cells = [
        value
        for table in payload["tables"]
        for row in table["rows"]
        for value in row["cells"].values()
    ]
    assert "150" not in cells  # It belongs to the distinct 'trúng tuyển' row.
    assert {"0", "-"} <= set(cells)
    assert response.json()["trace"]["context"]["table_selection"]["matched_families"] == 1
