import json

from qnu.domains.knowledge.metadata import RetrievalAnnotation
from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)


class SupplementChat(FakeChat):
    def _respond(self, index):
        status, raw = super()._respond(index)
        body = json.loads(raw)
        message = body["choices"][0]["message"]
        result = json.loads(message["content"])
        projected = json.loads(self.requests[index]["body"]["messages"][-1]["content"])
        citation = next(
            ref for ref in projected["allowed_citations"] if ref.endswith("ev_p001_b001")
        )
        result["metadata"] = [
            {
                "field": "PHỤ LỤC",
                "value": value,
                "citation": citation,
                "quote": quote,
                "scope": "section",
            }
            for value, quote in [
                ("01", "PHỤ LỤC 01"),
                ("99", "PHỤ LỤC 01"),
                ("02", "PHỤ LỤC 02"),
            ]
        ]
        message["content"] = json.dumps(result, ensure_ascii=False)
        return status, json.dumps(body, ensure_ascii=False).encode()


def test_source_draft_plus_ai_and_confirmed_json_through_api(client):
    data = processed_input(client, code="supplement-879")
    with SupplementChat() as chat:
        chat_provider(client, data, chat.base_url)
        quick = request_compile(client, data, key="quick-879", source_first=True)
        assert quick.status_code == 201, quick.text
        quick_id = quick.json()["run"]["id"]
        assert execute_compile(client, quick_id) == "completed"
        quick_draft = client.get(f"{data['url']}/{quick_id}/draft").json()

        created = request_compile(client, data, ai_supplement=True, structured_output=True)
        assert created.status_code == 201, created.text
        assert created.json()["run"]["ai_supplement"] is True
        run_id = created.json()["run"]["id"]
        assert execute_compile(client, run_id) == "completed"
        assert chat.requests
        draft_url = f"{data['url']}/{run_id}/draft"
        draft = client.get(draft_url).json()
        assert draft["sections"] == quick_draft["sections"]
        assert draft["source_tables"] == quick_draft["source_tables"]
        assert draft["citations"] == quick_draft["citations"]
        assert draft["supplement"]["input_sha256"] == created.json()["run"]["input_sha256"]
        assert draft["supplement"]["sections"]
        proposals = draft["supplement"]["metadata"]
        assert [item["origin"] for item in proposals] == ["model", "rules", "rules"], proposals
        assert [item["annotation"]["values"] for item in proposals[1:]] == [
            {"data_year": 2023},
            {"data_year": 2024},
        ]
        proposal = proposals[0]
        assert proposal["origin"] == "model"
        assert proposal["source"]["page"] == 1
        assert proposal["annotation"]["target"].startswith("section:")
        assert proposal["annotation"]["values"] == {"attributes": {"PHỤ LỤC": "01"}}

        url = data["url"].replace("/compilation-runs", "/compiled-documents")
        body = {"document_key": "supplement", "title": "Metadata", "compilation_run_id": run_id}
        headers = {"Idempotency-Key": "register-supplement"}
        invalid = client.post(
            url,
            headers=headers,
            json={
                **body,
                "metadata_proposal_ids": ["a" * 64],
            },
        )
        assert invalid.status_code == 422, invalid.text
        body["metadata_proposal_ids"] = [proposal["id"]]
        # Human edits keep the original target and proof citation. The server
        # must reject invented values/quotes before registration has any effect.
        body["metadata_proposal_edits"] = {
            proposal["id"]: {
                "values": {"attributes": {"PHỤ LỤC": "99"}},
                "quote": "PHỤ LỤC 01",
            }
        }
        invalid_edit = client.post(url, headers=headers, json=body)
        assert invalid_edit.status_code == 422, invalid_edit.text
        body["metadata_proposal_edits"][proposal["id"]]["values"]["attributes"]["PHỤ LỤC"] = "01"
        body["metadata_proposal_edits"][proposal["id"]]["quote"] = "PHỤ LỤC 01"
        registered = client.post(url, headers=headers, json=body)
        assert registered.status_code == 201, registered.text
        version = registered.json()["version"]
        assert [
            RetrievalAnnotation.model_validate(item).model_dump(mode="json", exclude_none=True)
            for item in version["retrieval_metadata"]
        ] == [proposal["annotation"]]
        assert version["provenance"]["metadata_confirmation"]["status"] == "confirmed"
        assert version["provenance"]["metadata_confirmation"]["edited_proposal_ids"] == [
            proposal["id"]
        ]
        assert client.post(url, headers=headers, json=body).status_code == 200
        body["metadata_proposal_edits"][proposal["id"]]["quote"] = "PHỤ LỤC"
        conflict = client.post(url, headers=headers, json=body)
        assert conflict.status_code == 409, conflict.text
        assert client.get(draft_url).json() == draft
