"""Acceptance for direct uploads: stored bytes, versions, dedupe, idempotency, failure."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from qnu.domains.knowledge.artifacts.files import build_storage_key
from qnu.platform.config import get_settings
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    REVIEWER,
    add_member,
    add_revision,
    as_actor,
    create_collection,
    create_workspace,
    pdf_bytes,
    upload_source,
    workspace_with_editor,
)


class _FailingStore:
    """Adapter that fails like a full/unreachable object store."""

    driver = "failing"

    async def put_bytes(self, key: str, payload: bytes, content_type: str | None = None) -> str:
        raise OSError("storage is unavailable")

    async def get_bytes(self, key: str) -> bytes:
        raise OSError("storage is unavailable")

    async def exists(self, key: str) -> bool:
        return False

    async def delete(self, key: str) -> None:
        return None


def _storage_path(workspace_id: str, collection_id: str, sha256: str) -> Path:
    root = Path(get_settings().LOCAL_STORAGE_PATH).resolve()
    return root / build_storage_key(workspace_id, collection_id, sha256)


def test_upload_requires_authentication(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Xác thực")
    as_actor(None)
    response = upload_source(client, workspace["id"], collection["id"])
    assert response.status_code == 401


def test_reviewer_cannot_upload(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Phân quyền")
    as_actor(REVIEWER)
    response = upload_source(client, workspace["id"], collection["id"])
    assert response.status_code == 403
    assert response.json()["code"] == "workspace_forbidden"


def test_upload_stores_bytes_and_metadata(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Nạp tài liệu")
    payload = pdf_bytes("de-an-2026")

    response = upload_source(
        client,
        workspace["id"],
        collection["id"],
        payload=payload,
        filename="../../Đề án 2026.pdf",
        title="Đề án tuyển sinh",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    source = body["source"]
    revision = body["revision"]
    assert source["status"] == "stored"
    assert source["title"] == "Đề án tuyển sinh"
    assert source["created_by"] == EDITOR.actor_id
    assert source["revision_count"] == 1
    assert source["current_revision_no"] == 1
    assert source["file_name"] == "Đề án 2026.pdf"
    assert source["size_bytes"] == len(payload)
    assert source["sha256"] == hashlib.sha256(payload).hexdigest()
    assert revision["revision_no"] == 1
    assert revision["sha256"] == source["sha256"]

    detail = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources/{source['id']}"
    )
    assert detail.status_code == 200
    assert detail.json()["sha256"] == source["sha256"]

    listing = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources"
    )
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] == 1
    assert listing.json()["items"][0]["id"] == source["id"]


def test_download_returns_the_original_bytes(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Tải lại")
    payload = pdf_bytes("ban-goc")
    uploaded = upload_source(
        client, workspace["id"], collection["id"], payload=payload, filename="Quy chế.pdf"
    ).json()

    response = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
        f"/sources/{uploaded['source']['id']}/revisions/{uploaded['revision']['id']}/content"
    )
    assert response.status_code == 200, response.text
    assert response.content == payload
    assert hashlib.sha256(response.content).hexdigest() == uploaded["revision"]["sha256"]
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment; filename*=UTF-8''")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_new_revision_keeps_the_previous_version_readable(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Phiên bản")
    first_payload = pdf_bytes("v1")
    first = upload_source(
        client, workspace["id"], collection["id"], payload=first_payload
    ).json()
    source_id = first["source"]["id"]

    second_payload = pdf_bytes("v2")
    second = add_revision(
        client, workspace["id"], collection["id"], source_id, payload=second_payload
    )
    assert second.status_code == 201, second.text
    assert second.json()["revision"]["revision_no"] == 2
    assert second.json()["source"]["revision_count"] == 2
    assert second.json()["source"]["sha256"] == hashlib.sha256(second_payload).hexdigest()

    revisions = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
        f"/sources/{source_id}/revisions"
    )
    assert revisions.status_code == 200
    assert [item["revision_no"] for item in revisions.json()] == [2, 1]

    old = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
        f"/sources/{source_id}/revisions/{first['revision']['id']}/content"
    )
    assert old.status_code == 200
    assert old.content == first_payload
    assert hashlib.sha256(old.content).hexdigest() == first["revision"]["sha256"]


def test_duplicate_content_in_a_collection_is_rejected(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Trùng nội dung")
    payload = pdf_bytes("trung")
    first = upload_source(client, workspace["id"], collection["id"], payload=payload)
    assert first.status_code == 201

    duplicate = upload_source(
        client, workspace["id"], collection["id"], payload=payload, filename="khac-ten.pdf"
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_content"

    listing = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources"
    )
    assert listing.json()["meta"]["total"] == 1


def test_unchanged_revision_is_rejected(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Không đổi")
    payload = pdf_bytes("same")
    uploaded = upload_source(client, workspace["id"], collection["id"], payload=payload).json()

    again = add_revision(
        client,
        workspace["id"],
        collection["id"],
        uploaded["source"]["id"],
        payload=payload,
    )
    assert again.status_code == 409
    assert again.json()["code"] == "revision_unchanged"


def test_idempotency_replays_the_same_result(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Idempotency")
    payload = pdf_bytes("idem")

    first = upload_source(
        client, workspace["id"], collection["id"], payload=payload, idempotency_key="key-0001"
    )
    assert first.status_code == 201, first.text
    replay = upload_source(
        client, workspace["id"], collection["id"], payload=payload, idempotency_key="key-0001"
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["source"]["id"] == first.json()["source"]["id"]
    assert replay.json()["revision"]["id"] == first.json()["revision"]["id"]

    listing = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources"
    )
    assert listing.json()["meta"]["total"] == 1


def test_idempotency_key_reused_for_another_request_conflicts(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Idempotency conflict")
    upload_source(
        client,
        workspace["id"],
        collection["id"],
        payload=pdf_bytes("a"),
        idempotency_key="key-0002",
    )
    conflict = upload_source(
        client,
        workspace["id"],
        collection["id"],
        payload=pdf_bytes("b"),
        idempotency_key="key-0002",
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_created_by_cannot_be_forged(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Giả danh")
    response = upload_source(
        client,
        workspace["id"],
        collection["id"],
        payload=pdf_bytes("forge"),
        extra_data={"created_by": "ke-gia-mao", "actor_ref": "ke-gia-mao"},
        extra_headers={"X-Actor-Ref": "ke-gia-mao", "X-User": "ke-gia-mao"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["source"]["created_by"] == EDITOR.actor_id
    assert response.json()["revision"]["created_by"] == EDITOR.actor_id


def test_unsupported_and_mismatched_files_are_rejected(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Định dạng")

    unsupported = upload_source(
        client,
        workspace["id"],
        collection["id"],
        payload=b"MZ\x90\x00",
        filename="doc.exe",
        content_type="application/octet-stream",
    )
    assert unsupported.status_code == 415
    assert unsupported.json()["code"] == "unsupported_file_type"

    mismatched = upload_source(
        client, workspace["id"], collection["id"], payload=b"khong-phai-pdf", filename="gia.pdf"
    )
    assert mismatched.status_code == 415
    assert mismatched.json()["code"] == "file_signature_mismatch"

    listing = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources"
    )
    assert listing.json()["meta"]["total"] == 0


def test_source_from_another_workspace_or_collection_is_not_found(client: TestClient) -> None:
    workspace_a = create_workspace(client, "khoa-a")
    workspace_b = create_workspace(client, "khoa-b")
    for workspace in (workspace_a, workspace_b):
        add_member(client, workspace["id"], EDITOR.actor_id, "editor")

    as_actor(EDITOR)
    collection_a = create_collection(client, workspace_a["id"], "Của A")
    collection_b = create_collection(client, workspace_b["id"], "Của B")
    uploaded = upload_source(
        client, workspace_a["id"], collection_a["id"], payload=pdf_bytes("a-only")
    ).json()

    cross_workspace = client.get(
        f"{API}/workspaces/{workspace_b['id']}/collections/{collection_b['id']}"
        f"/sources/{uploaded['source']['id']}"
    )
    assert cross_workspace.status_code == 404
    assert cross_workspace.json()["code"] == "source_not_found"

    other_collection = client.get(
        f"{API}/workspaces/{workspace_a['id']}/collections/{collection_b['id']}"
        f"/sources/{uploaded['source']['id']}"
    )
    assert other_collection.status_code == 404

    content = client.get(
        f"{API}/workspaces/{workspace_a['id']}/collections/{collection_b['id']}"
        f"/sources/{uploaded['source']['id']}/revisions/{uploaded['revision']['id']}/content"
    )
    assert content.status_code == 404


def test_storage_failure_does_not_create_a_source(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Lỗi storage")
    container = client.app.state.container
    original = container.blob_store
    container.blob_store = _FailingStore()
    try:
        response = upload_source(
            client, workspace["id"], collection["id"], payload=pdf_bytes("storage-fail")
        )
    finally:
        container.blob_store = original

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    listing = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources"
    )
    assert listing.json()["meta"]["total"] == 0


def test_missing_blob_is_reported_instead_of_an_empty_file(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Mất blob")
    payload = pdf_bytes("missing")
    uploaded = upload_source(
        client, workspace["id"], collection["id"], payload=payload
    ).json()
    path = _storage_path(
        workspace["id"], collection["id"], uploaded["revision"]["sha256"]
    )
    path.unlink()

    response = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
        f"/sources/{uploaded['source']['id']}/revisions/{uploaded['revision']['id']}/content"
    )
    assert response.status_code == 502
    assert response.json()["code"] == "blob_missing"


def test_tampered_blob_fails_the_checksum_check(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Sai checksum")
    uploaded = upload_source(
        client, workspace["id"], collection["id"], payload=pdf_bytes("tamper")
    ).json()
    path = _storage_path(workspace["id"], collection["id"], uploaded["revision"]["sha256"])
    path.write_bytes(b"%PDF-1.7\n% bi sua trai phep\n%%EOF\n")

    response = client.get(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}"
        f"/sources/{uploaded['source']['id']}/revisions/{uploaded['revision']['id']}/content"
    )
    assert response.status_code == 502
    assert response.json()["code"] == "blob_integrity_failed"
