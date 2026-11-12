"""The real review API keeps contextual proposals separate from authorized saves."""

import json

from tests.integration.compiler_support import chat_provider, processed_input
from tests.integration.test_ocr_text_review_651 import (
    FakeSpeller,
    detect,
    edit_body,
    review_url,
    save,
)


def test_context_uses_pinned_text_and_schema_never_allows_read_only_ids(client):
    data = processed_input(client, code="spelling801-context")
    url = review_url(data)
    current = client.get(url).json()
    # Inspect a table cell: the neighboring row name and heading must travel with it.
    target = next(u for u in current["units"] if u["kind"] == "table_cell" and u["text"])
    with FakeSpeller() as model:
        chat_provider(client, data, model.base_url)
        body = {
            "expected_version": current["version"],
            "expected_sha256": current["canonical_sha256"],
            "evidence_ids": [target["evidence_id"]],
        }
        # Loopback proves the wire contract, never Vietnamese model accuracy.
        response = client.post(
            url + "/checks", json=body, headers={"Idempotency-Key": "context801"}
        )
        assert response.status_code == 200, response.text
        assert len(model.requests) == 1
        request = model.requests[0]["body"]
        prompt = json.loads(request["messages"][-1]["content"])
        assert prompt["text_version"] == current["version"]
        assert prompt["canonical_sha256"] == current["canonical_sha256"]
        assert prompt["source_image_verified"] is False
        assert prompt["context"] and all(c["read_only"] for c in prompt["context"])
        schema = request["response_format"]["json_schema"]["schema"]
        props = schema["$defs"]["ContextSuggestion"]
        assert props["properties"]["evidence_id"]["enum"] == [target["evidence_id"]]
        assert {"context_before", "context_after"} <= set(props["required"])
        assert client.get(url).json()["version"] == 0


class LexicalSpeller(FakeSpeller):
    def _respond(self, index):
        unit = json.loads(self.requests[index]["body"]["messages"][-1]["content"])["units"][0]
        text = unit["text"]
        start = text.index("bán")
        suggestion = {
            "evidence_id": unit["evidence_id"],
            "start": start,
            "end": start + 3,
            "original": "bán",
            "replacement": "huyên",
            "reason": "Một suy đoán sai của model.",
            "context_before": text,
            "context_after": text[:start] + "huyên" + text[start + 3 :],
        }
        return 200, json.dumps(
            {
                "choices": [
                    {
                        "message": {"content": json.dumps({"suggestions": [suggestion]})},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
            }
        ).encode()


def test_bad_lexical_guess_is_visible_but_never_in_apply_list_or_saved_automatically(client):
    data = processed_input(client, code="spelling801-guess")
    url = review_url(data)
    current = client.get(url).json()
    text = "Có xác nhận của bệnh viện cấp cơ bán trở lên."
    current = save(client, url, edit_body(current, current["units"][0], text)).json()
    before = client.get(url + "/document").content
    with LexicalSpeller() as model:
        chat_provider(client, data, model.base_url)
        response = detect(client, data, current)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["suggestions"] == []
        assert result["withheld_suggestions"][0]["review_reason"] == "source_image_required"
        assert result["withheld_suggestions"][0]["context_after"].endswith("cơ huyên trở lên.")
        fetched = client.get(url + "/checks/" + result["id"]).json()
        assert fetched["withheld_suggestions"] == result["withheld_suggestions"]
        assert detect(client, data, current).json()["id"] == result["id"]
        assert len(model.requests) == 1
    assert client.get(url + "/document").content == before
    assert client.get(url).json()["version"] == current["version"]


def test_context_never_certifies_an_unrelated_full_sentence_rewrite(client):
    class RewritingSpeller(FakeSpeller):
        def _respond(self, index):
            status, payload = super()._respond(index)
            result = json.loads(payload)
            response = json.loads(result["choices"][0]["message"]["content"])
            response["suggestions"][0]["context_after"] += " Thêm dữ kiện 2027."
            result["choices"][0]["message"]["content"] = json.dumps(response)
            return status, json.dumps(result).encode()

    data = processed_input(client, code="spelling801-proof")
    current = client.get(review_url(data)).json()
    with RewritingSpeller() as model:
        chat_provider(client, data, model.base_url)
        response = detect(client, data, current)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "completed"
        assert result["suggestions"] == []
        assert result["rejected_suggestions"] == []
        assert result["withheld_suggestions"][0]["review_reason"] == "context_unverified"
        replay = detect(client, data, current)
        assert replay.json()["id"] == result["id"]
        assert len(model.requests) == 1
    assert client.get(review_url(data)).json()["version"] == 0
