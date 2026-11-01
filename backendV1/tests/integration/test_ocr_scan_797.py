"""Real handler/DB boundaries; loopback OCR does not assert model accuracy."""

import json

import pytest

from qnu.domains.ocr.models import OcrProcessingRun
from qnu.platform.database import AsyncSessionFactory
from tests.integration.compiler_support import chat_provider, processed_input
from tests.integration.knowledge_support import REVIEWER, as_actor
from tests.integration.ocr_support import (
    FakeNemotron,
    execute_now,
    runs_url,
    setup_ocr_provider,
)
from tests.integration.test_ocr_processing_api import _workspace_with_document
from tests.integration.test_ocr_text_review_651 import FakeSpeller, detect, review_url


def test_explicit_density_is_pinned_in_a_new_generation_and_old_artifacts_survive(client):
    with FakeNemotron() as fake:
        ws, col, source, rev = _workspace_with_document(client, "scan797-dpi")
        setup_ocr_provider(client, ws["id"], fake.base_url)
        url = runs_url(ws["id"], col["id"], source["id"], rev["id"])
        first = client.post(url, json={}).json()["run"]
        assert execute_now(client, first["id"]).status == "completed"
        original = client.get(f"{url}/{first['id']}/document").content
        created = client.post(url, json={"render_dpi": 176})
        assert created.status_code == 201
        second = created.json()["run"]
        assert second["generation"] == first["generation"] + 1
        assert second["config_fingerprint"] != first["config_fingerprint"]
        assert client.get(f"{url}/{first['id']}/document").content == original

        async def pinned():
            async with AsyncSessionFactory() as db:
                return (await db.get(OcrProcessingRun, second["id"])).config

        config = client.portal.call(pinned)
        assert config["renderer"]["dpi"] == 176
        assert config["ocr"]["table_layout_version"] == "nemotron-tabular/v2"
        repeated = client.post(url, json={"render_dpi": 176})
        assert repeated.status_code == 200
        assert repeated.json()["run"]["id"] == second["id"]
        assert execute_now(client, second["id"]).status == "completed"
        assert client.get(f"{url}/{first['id']}/document").content == original


@pytest.mark.parametrize("dpi", [0, 71, 301])
def test_invalid_density_cannot_create_a_run(client, dpi):
    ws, col, source, rev = _workspace_with_document(client, "scan797-range")
    url = runs_url(ws["id"], col["id"], source["id"], rev["id"])
    assert client.post(url, json={"render_dpi": dpi}).status_code == 422
    assert client.get(url).json()["meta"]["total"] == 0


def test_density_override_does_not_bypass_write_permission(client):
    ws, col, source, rev = _workspace_with_document(client, "scan797-access")
    as_actor(REVIEWER)
    url = runs_url(ws["id"], col["id"], source["id"], rev["id"])
    assert client.post(url, json={"render_dpi": 176}).status_code == 403


def test_model_offsets_are_anchored_before_display_and_do_not_write_a_text_version(client):
    class OffsetSpeller(FakeSpeller):
        def _respond(self, index):
            status, payload = super()._respond(index)
            body = json.loads(payload)
            suggestions = json.loads(body["choices"][0]["message"]["content"])
            suggestions["suggestions"][0].update(start=50, end=53)
            body["choices"][0]["message"]["content"] = json.dumps(suggestions)
            return status, json.dumps(body).encode()

    data = processed_input(client, code="anchor797-api")
    current = client.get(review_url(data)).json()
    with OffsetSpeller() as model:
        chat_provider(client, data, model.base_url)
        result = detect(client, data, current)
        assert result.status_code == 200, result.text
        suggestion = result.json()["suggestions"][0]
        assert (suggestion["start"], suggestion["end"]) == (0, 3)
        assert client.get(review_url(data)).json()["version"] == 0
        assert len(model.requests) == 1
        output = model.requests[0]["body"]["response_format"]
        assert output["type"] == "json_schema"
        assert output["json_schema"]["schema"]["required"] == ["suggestions"]
