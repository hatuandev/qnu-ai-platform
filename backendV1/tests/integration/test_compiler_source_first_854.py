from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)


def test_fast_compilation_keeps_source_and_creates_no_model_requests(client):
    data = processed_input(client, code="source-first854")
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url, secret=None)
        response = request_compile(client, data, source_first=True)
        assert response.status_code == 201, response.text
        run = response.json()["run"]
        assert run["source_first"] is True
        assert execute_compile(client, run["id"]) == "completed"
        assert not chat.requests

        base = data["url"] + "/" + run["id"]
        plain = client.get(base + "/draft")
        draft = plain.json()
        view = client.get(base + "/draft", params={"group_by_source": "true"})
        assert view.status_code == 200
        assert view.headers["etag"] != plain.headers["etag"]
        grouped = view.json()
        groups = grouped.pop("reading_groups")
        assert grouped == draft
        assert [position for group in groups for position in group["paragraphs"]] == [
            [s, p]
            for s, section in enumerate(draft["sections"])
            for p in range(len(section["paragraphs"]))
        ]
        assert draft["validation"]["source_copy"] == "retained"
        assert draft["validation"]["semantic_faithfulness"] == "not_evaluated"
        paragraphs = [p for section in draft["sections"] for p in section["paragraphs"]]
        assert paragraphs and all(
            ref in draft["citations"] for p in paragraphs for ref in p["citations"]
        )
        assert client.get(base + "/markdown").status_code == 200
        assert client.get(base + "/auto-review").status_code == 404
        assert request_compile(client, data, source_first=True).json()["run"]["id"] == run["id"]
        assert request_compile(client, data).status_code == 409
