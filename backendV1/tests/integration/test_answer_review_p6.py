"""Answer tests use the real answer pipeline; human labels stay beside gold data."""

from tests.integration.knowledge_support import (
    API,
    EDITOR,
    MEMBER,
    PLATFORM,
    as_actor,
    create_collection,
)
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401


def assistants_url(data):
    return f"{API}/workspaces/{data['workspace']['id']}/assistants"


def create_assistant(client, data, *, collection_id=None):
    as_actor(PLATFORM)
    response = client.post(
        assistants_url(data),
        json={
            "name": "Trợ lý kiểm thử",
            "collection_id": collection_id or data["collection"]["id"],
            "chat_provider_id": data["chat_provider"]["id"],
        },
    )
    assert response.status_code == 201, response.text
    as_actor(EDITOR)
    return response.json()


def reviews_url(data, assistant_id):
    return assistants_url(data) + f"/{assistant_id}/answer-reviews"


def update_assistant(client, data, assistant, **changes):
    as_actor(PLATFORM)
    body = {
        key: assistant[key]
        for key in (
            "name",
            "description",
            "persona",
            "collection_id",
            "chat_provider_id",
            "top_k",
            "history_turns",
            "max_output_tokens",
            "rag_policy",
            "is_active",
        )
    }
    body.update(changes, expected_revision=assistant["revision"])
    response = client.put(assistants_url(data) + "/" + assistant["id"], json=body)
    assert response.status_code == 200, response.text
    as_actor(EDITOR)
    return response.json()


def test_review_runs_on_published_sources_and_stores_human_labels(client, ready):  # noqa: F811
    assistant = create_assistant(client, ready)
    url = reviews_url(ready, assistant["id"])
    questions = [
        "Chỉ tiêu tuyển sinh năm 2024 là bao nhiêu?",
        "Ngành nào có chỉ tiêu cao nhất?",
    ]
    response = client.post(
        url,
        headers={"Idempotency-Key": "review-one"},
        json={"questions": questions},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["assistant_revision"] == assistant["revision"]
    assert body["question_count"] == 2
    assert [item["question"] for item in body["items"]] == questions
    assert [item["status"] for item in body["items"]] == ["answered", "answered"]
    first = body["items"][0]
    assert first["result"]["status"] == "answered"
    assert "150" in first["result"]["answer"]
    assert first["result"]["index_run_id"] == ready["index_run"]["id"]
    assert first["index_run_id"] == ready["index_run"]["id"]
    assert first["generation"] >= 1
    assert first["result"]["trace"]["provider_id"] == ready["chat_provider"]["id"]
    assert first["result"]["sources"]
    assert all(
        citation["revision_id"] == ready["revision"]["id"]
        for source in first["result"]["sources"]
        for citation in source["citations"].values()
    )

    as_actor(MEMBER)
    denied = client.put(
        url + f"/{body['id']}/items/{first['id']}", json={"label": "correct"}
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["code"] == "workspace_forbidden"

    as_actor(EDITOR)
    labelled = client.put(
        url + f"/{body['id']}/items/{first['id']}",
        json={"label": "correct", "note": "Khớp bảng công bố."},
    )
    assert labelled.status_code == 200, labelled.text
    item = labelled.json()["items"][0]
    assert item["label"] == "correct"
    assert item["label_note"] == "Khớp bảng công bố."
    assert item["labelled_by"] == EDITOR.actor_id
    assert item["result"]["id"] == first["result"]["id"]

    detail = client.get(url + "/" + body["id"])
    assert detail.status_code == 200, detail.text
    assert detail.json()["items"][0]["label"] == "correct"
    listing = client.get(url)
    assert listing.status_code == 200, listing.text
    assert [row["id"] for row in listing.json()] == [body["id"]]

    replay = client.post(
        url,
        headers={"Idempotency-Key": "review-one"},
        json={"questions": questions},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == body["id"]
    assert replay.json()["items"][0]["label"] == "correct"
    conflict = client.post(
        url,
        headers={"Idempotency-Key": "review-one"},
        json={"questions": ["Câu hỏi khác"]},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"

    update_assistant(client, ready, assistant, name="Trợ lý đổi tên")
    pinned = client.get(url + "/" + body["id"])
    assert pinned.json()["assistant_revision"] == assistant["revision"]


def test_review_keeps_insufficient_evidence_truthful(client, ready):  # noqa: F811
    ready["answer_chat"].mode = "abstain"
    assistant = create_assistant(client, ready)
    url = reviews_url(ready, assistant["id"])
    response = client.post(
        url,
        headers={"Idempotency-Key": "review-abstain"},
        json={"questions": ["Chỉ tiêu tuyển sinh năm 2024 là bao nhiêu?"]},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    item = body["items"][0]
    assert item["status"] == "insufficient_evidence"
    assert item["result"]["status"] == "insufficient_evidence"
    assert item["result"]["reason"] == "model_abstained"
    assert item["result"]["answer"] is None
    assert item["result"]["sources"] == []
    labelled = client.put(
        url + f"/{body['id']}/items/{item['id']}",
        json={"label": "missing", "note": "Bảng chưa có số năm 2024."},
    )
    assert labelled.status_code == 200, labelled.text
    assert labelled.json()["items"][0]["label"] == "missing"
    assert labelled.json()["items"][0]["result"]["answer"] is None


def test_review_records_provider_failure_per_item(client, ready):  # noqa: F811
    ready["answer_chat"].mode = "http_error"
    assistant = create_assistant(client, ready)
    url = reviews_url(ready, assistant["id"])
    response = client.post(
        url,
        headers={"Idempotency-Key": "review-provider-error"},
        json={"questions": ["Chỉ tiêu tuyển sinh năm 2024 là bao nhiêu?"]},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "failed"
    item = body["items"][0]
    assert item["status"] == "failed"
    assert item["error_code"] == "chat_provider_unavailable"
    assert item["result"] is None
    denied = client.put(
        url + f"/{body['id']}/items/{item['id']}", json={"label": "correct"}
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "answer_review_item_not_ready"


def test_review_requires_active_assistant_with_published_sources(client, ready):  # noqa: F811
    empty = create_collection(client, ready["workspace"]["id"], "Bộ sưu tập trống")
    empty_assistant = create_assistant(client, ready, collection_id=empty["id"])
    refused = client.post(
        reviews_url(ready, empty_assistant["id"]),
        headers={"Idempotency-Key": "review-empty"},
        json={"questions": ["Có tài liệu nào không?"]},
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "assistant_no_published_sources"

    assistant = create_assistant(client, ready)
    update_assistant(client, ready, assistant, is_active=False)
    paused = client.post(
        reviews_url(ready, assistant["id"]),
        headers={"Idempotency-Key": "review-paused"},
        json={"questions": ["Chỉ tiêu tuyển sinh năm 2024 là bao nhiêu?"]},
    )
    assert paused.status_code == 409
    assert paused.json()["code"] == "assistant_inactive"
