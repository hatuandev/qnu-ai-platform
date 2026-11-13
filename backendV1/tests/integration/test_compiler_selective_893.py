import json

import pytest

from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.ocr_support import TABLE_RESPONSE, ocr_blocks


class SelectiveChat(FakeChat):
    def _respond(self, index):
        status, raw = super()._respond(index)
        if self.mode != "ok":
            return status, raw
        body = json.loads(raw)
        message = body["choices"][0]["message"]
        request = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        owned = request["part"]["owned"][0]
        citation = f"{owned['ocr_run_id']}:{owned['evidence_id']}"
        message["content"] = json.dumps(
            {
                "sections": [
                    {
                        "heading": "Thông tin văn bản",
                        "paragraphs": [{"text": "Số hiệu: 07/AB", "citations": [citation]}],
                    },
                    {
                        "heading": "Định danh văn bản",
                        "paragraphs": [
                            {"text": "Khối này xác định số hiệu văn bản.", "citations": [citation]}
                        ],
                    },
                ],
                "unknowns": [],
                "metadata": [
                    {
                        "field": "Số hiệu",
                        "value": "07/AB",
                        "citation": citation,
                        "quote": "Số hiệu: 07/AB",
                    },
                ],
            },
            ensure_ascii=False,
        )
        return status, json.dumps(body).encode()


def test_selective_compilation_skips_model_for_structured_source(client):
    data = processed_input(client, code="selective-structured")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        response = request_compile(client, data, selective_supplement=True)
        assert response.status_code == 201, response.text
        run = response.json()["run"]
        assert run["selective_supplement"]
        assert execute_compile(client, run["id"]) == "completed"
        assert not chat.requests
        draft = client.get(f"{data['url']}/{run['id']}/draft").json()
        assert draft["supplement"]["state"] == "skipped"
        assert draft["source_tables"]
        assert draft["citations"]


@pytest.mark.parametrize("mode", ["ok", "bad_schema", "truncated"])
def test_selective_compilation_keeps_source_draft_and_reports_model_outcome(client, mode):
    data = processed_input(
        client,
        code=f"selective-{mode}",
        response=TABLE_RESPONSE
        + ocr_blocks("Số hiệu: 07/AB|Text")
        .replace("<y_0.05>", "<y_0.53>")
        .replace("<y_0.13>", "<y_0.61>"),
    )
    with SelectiveChat() as chat:
        chat_provider(client, data, chat.base_url)
        chat.mode = mode
        quick = request_compile(client, data, key="source-draft", source_first=True).json()["run"]
        assert execute_compile(client, quick["id"]) == "completed"
        source_draft = client.get(f"{data['url']}/{quick['id']}/draft").json()
        response = request_compile(client, data, selective_supplement=True)
        assert response.status_code == 201, response.text
        run_id = response.json()["run"]["id"]
        url = f"{data['url']}/{run_id}/draft"
        assert client.get(url, params={"partial": True}).status_code == 404

        assert execute_compile(client, run_id) == "completed"
        assert len(chat.requests) == 1
        request = json.loads(chat.requests[0]["body"]["messages"][-1]["content"])
        assert [item["evidence_id"] for item in request["part"]["owned"]] == ["ev_p001_b004"]
        preview = client.get(url, params={"partial": True, "group_by_source": True}).json()
        assert preview["reading_groups"]
        draft = client.get(url).json()
        for key in ("sections", "source_tables", "citations"):
            assert draft[key] == preview[key] == source_draft[key]
        assert not draft["partial"]
        supplement = draft["supplement"]
        if mode == "ok":
            assert supplement["state"] == "completed"
            sections = supplement["sections"][0]["sections"]
            assert [section["heading"] for section in sections] == ["Định danh văn bản"]
            metadata = supplement["metadata"]
            assert [item["origin"] for item in metadata] == ["model", "rules", "rules"]
            assert [item["annotation"]["values"] for item in metadata] == [
                {"attributes": {"Số hiệu": "07/AB"}},
                {"data_year": 2023},
                {"data_year": 2024},
            ]
        else:
            assert supplement["state"] == "incomplete"
            failure_code = (
                "compilation_refinement_atomic_limit"
                if mode == "truncated"
                else "compilation_draft_invalid"
            )
            assert supplement["failure_code"] == failure_code
            # The provider's original error remains on the failed request.
            code = "chat_output_truncated" if mode == "truncated" else failure_code
            assert supplement["incomplete_groups"] == [
                {"index": 1, "status": "failed", "code": code},
            ]
            assert not draft["compilation_nodes"]


class PartialSelectiveChat(SelectiveChat):
    def _respond(self, index):
        self.mode = "truncated" if index == 0 else "ok" if index == 1 else "bad_schema"
        return super()._respond(index)


def test_selective_compilation_keeps_completed_children_once(client):
    metadata = ocr_blocks("Số hiệu: 07/AB|Text", "Số văn bản: 08/CD|Text")
    metadata = (
        metadata.replace("<y_0.05>", "<y_0.53>")
        .replace("<y_0.13>", "<y_0.61>")
        .replace("<y_0.17>", "<y_0.65>")
        .replace("<y_0.25>", "<y_0.73>")
    )
    data = processed_input(client, code="selective-children", response=TABLE_RESPONSE + metadata)
    with PartialSelectiveChat() as chat:
        chat_provider(client, data, chat.base_url)
        response = request_compile(client, data, selective_supplement=True)
        assert response.status_code == 201, response.text
        run_id = response.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        assert len(chat.requests) == 3  # One parent and two distinct children.
        draft = client.get(f"{data['url']}/{run_id}/draft").json()
        assert draft["supplement"]["state"] == "incomplete"
        assert len(draft["supplement"]["sections"]) == 1
        metadata = draft["supplement"]["metadata"]
        assert [item["origin"] for item in metadata] == ["model", "rules", "rules"]
        assert [item["annotation"]["values"] for item in metadata[1:]] == [
            {"data_year": 2023},
            {"data_year": 2024},
        ]
        assert draft["source_tables"]
        assert [node["index"] for node in draft["compilation_nodes"]] == [2]
