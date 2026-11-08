from tests.integration.compiler_support import (
    FakeChat,
    chat_provider,
    execute_compile,
    processed_input,
    request_compile,
)
from tests.integration.knowledge_support import EDITOR, OUTSIDER, as_actor
from tests.integration.ocr_support import ocr_blocks


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
