"""Workflow fixtures use real API/DB and the loopback review protocol fixture."""

from tests.integration.test_compiler_review_652 import prepared  # noqa: F401


def run_review(client, run_id):
    from qnu.main import app
    from qnu.workers.tasks.compilation import compiler_review_job

    return client.portal.call(compiler_review_job, {"container": app.state.container}, run_id)


def mutate(client, model, row_id, **values):
    from qnu.platform.database import AsyncSessionFactory

    async def change():
        async with AsyncSessionFactory() as db:
            row = await db.get(model, row_id)
            for key, value in values.items():
                setattr(row, key, value)
            await db.commit()

    client.portal.call(change)


def base_url(data):
    return data["url"] + "/" + data["run_id"]


def preview_edit(client, data, *, review_id=None):
    url = base_url(data)
    current = client.get(url + "/edit-context")
    assert current.status_code == 200, current.text
    body = {
        "expected_bundle_sha256": current.json()["bundle_sha256"],
        "reason": "Bổ sung giới hạn theo ghi chú nguồn.",
        "content": current.json()["content"],
        "review_id": review_id,
    }
    body["content"]["sections"][0]["paragraphs"][0]["text"] += " Phạm vi được người dùng làm rõ."
    result = client.post(url + "/edit-previews", json=body)
    assert result.status_code == 200, result.text
    return result.json(), body


def accept_edit(client, data, preview, key="accept-one"):
    return client.post(
        base_url(data) + "/edits",
        json={"preview_id": preview["preview_id"], "preview_sha256": preview["preview_sha256"]},
        headers={"Idempotency-Key": key},
    )
