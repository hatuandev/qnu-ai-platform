from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import EDITOR, OUTSIDER, PLATFORM, as_actor
from tests.integration.ocr_support import ocr_blocks
from tests.integration.publication_review_support import acknowledgement


def test_preview_register_replay_stale_and_access_through_real_api(client):
    data = processed_input(
        client,
        code="automatic-896",
        response=ocr_blocks(
            "Thông tin tuyển sinh năm 2026|Title",
            "Mã đơn vị: 0012|Text",
        ),
    )
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        created = request_compile(client, data, source_first=True)
    assert created.status_code == 201, created.text
    run_id = created.json()["run"]["id"]
    assert execute_compile(client, run_id) == "completed"
    url = data["url"].replace("/compilation-runs", "/compiled-documents")
    endpoint = f"{url}/registration-metadata/{run_id}"
    draft_url = f"{data['url']}/{run_id}/draft"
    original = client.get(draft_url).json()
    as_actor(OUTSIDER)
    assert client.get(endpoint).status_code == 404
    as_actor(EDITOR)
    response = client.get(endpoint)
    assert response.status_code == 200, response.text
    information = response.json()
    assert information["annotations"]
    fields = [a["values"] for a in information["annotations"]]
    assert any(v["data_year"] == 2026 for v in fields)
    assert not any(v["program"] or v["intake"] for v in fields)
    body = {
        "document_key": "automatic",
        "title": "Thông tin tuyển sinh",
        "compilation_run_id": run_id,
        "automatic_metadata_sha256": "0" * 64,
    }
    headers = {"Idempotency-Key": "register-automatic-896"}
    rejected = client.post(url, json=body, headers=headers)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "registration_metadata_changed"
    assert client.get(url).json() == []
    body["automatic_metadata_sha256"] = information["sha256"]
    saved = client.post(url, json=body, headers=headers)
    assert saved.status_code == 201, saved.text
    version = saved.json()["version"]
    assert version["status"] == "draft"
    assert version["retrieval_metadata"] == information["annotations"]
    assert version["provenance"]["automatic_metadata"]["status"] == "source_verified"
    assert "metadata_confirmation" not in version["provenance"]
    assert client.post(url, json=body, headers=headers).status_code == 200
    body["automatic_metadata_sha256"] = "1" * 64
    assert client.post(url, json=body, headers=headers).status_code == 409
    assert client.get(draft_url).json() == original


def decision(client, version_url, action):
    ack = acknowledgement(client, version_url)
    version = client.get(version_url).json()
    ack["retrieval_metadata_sha256"] = version["retrieval_metadata_sha256"]
    preview = client.post(
        version_url + "/decision-preview",
        json={
            "action": action,
            "reason": "Đã đối chiếu bản nháp với nguồn.",
            "review_ack": ack,
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    return client.post(
        version_url + "/decisions",
        headers={"Idempotency-Key": action},
        json={"preview_id": body["id"], "preview_sha256": body["preview_sha256"]},
    )


def test_automatic_metadata_version_stays_readable_approved_and_published(client):
    data = processed_input(
        client,
        code="automatic-896-lifecycle",
        response=ocr_blocks(
            "Thông tin tuyển sinh năm 2026|Title",
            "Mã đơn vị: 0012|Text",
        ),
    )
    with FakeChat() as chat:
        chat_provider(client, data, chat.base_url)
        created = request_compile(client, data, source_first=True)
    assert created.status_code == 201, created.text
    run_id = created.json()["run"]["id"]
    assert execute_compile(client, run_id) == "completed"
    base = data["url"].replace("/compilation-runs", "/compiled-documents")
    information = client.get(f"{base}/registration-metadata/{run_id}").json()
    as_actor(EDITOR)
    saved = client.post(
        base,
        headers={"Idempotency-Key": "automatic-896-lifecycle"},
        json={
            "document_key": "automatic-lifecycle",
            "title": "Thông tin tuyển sinh",
            "compilation_run_id": run_id,
            "automatic_metadata_sha256": information["sha256"],
        },
    )
    assert saved.status_code == 201, saved.text
    registered = saved.json()
    doc_url = f"{base}/{registered['document']['id']}"
    version_url = f"{doc_url}/versions/{registered['version']['id']}"
    draft = client.get(version_url + "/draft")
    assert draft.status_code == 200, draft.text
    as_actor(PLATFORM)
    approved = decision(client, version_url, "approve")
    assert approved.status_code == 200, approved.text
    published = decision(client, version_url, "publish")
    assert published.status_code == 200, published.text
    served = client.get(doc_url + "/published")
    assert served.status_code == 200, served.text
    assert served.json()["version"]["status"] == "published"
