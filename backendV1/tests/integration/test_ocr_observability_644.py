"""API/worker acceptance using synthetic files and a loopback mock provider."""

import hashlib
import json

import pytest

from qnu.domains.ocr import execution, service
from tests.integration.knowledge_support import EDITOR, OUTSIDER, as_actor, workspace_with_editor
from tests.integration.ocr_support import (
    TABLE_RESPONSE,
    FakeJobQueue,
    FakeNemotron,
    docx_with_table,
    execute_now,
    prepare_source,
    real_pdf,
    request_run,
    runs_url,
    setup_ocr_provider,
)


class RecordedEvents:
    def __init__(self):
        self.events = []

    def info(self, event, **fields):
        self.events.append({"event": event, **fields})

    warning = info


def prepare(client, fake, name, *, docx=False, quota=1000000):
    workspace = workspace_with_editor(client, name)
    as_actor(EDITOR)
    payload = docx_with_table() if docx else real_pdf(["Synthetic OCR acceptance"])
    collection, source, revision = prepare_source(
        client,
        workspace["id"],
        name,
        payload=payload,
        filename="sample.docx" if docx else "sample.pdf",
    )
    provider = setup_ocr_provider(client, workspace["id"], fake.base_url, quota=quota)
    created = request_run(
        client,
        workspace["id"],
        collection["id"],
        source["id"],
        revision["id"],
        queue=FakeJobQueue(),
    )
    assert created.status_code == 201
    run = created.json()["run"]
    url = f"{runs_url(workspace['id'], collection['id'], source['id'], revision['id'])}/{run['id']}"
    return run, url, revision, provider


@pytest.mark.parametrize("docx", [False, True], ids=["pdf", "docx"])
def test_stages_correlate_worker_and_api_without_document_content(client, monkeypatch, docx):
    events = RecordedEvents()
    monkeypatch.setattr(execution, "logger", events)
    monkeypatch.setattr(service, "logger", events)
    with FakeNemotron() as fake:
        fake.responses = [TABLE_RESPONSE]
        run, url, revision, provider = prepare(
            client, fake, "trace-docx" if docx else "trace-pdf", docx=docx
        )
        assert execute_now(client, run["id"]).status == "completed"
        assert client.get(url + "/document").status_code == 200
        evidence = client.get(url + "/evidence").json()
        assert evidence["identity"]["source_sha256"] == revision["sha256"]
        assert {a["kind"] for a in evidence["artifacts"]} >= {
            "page_image",
            "raw_response",
            "canonical_json",
            "markdown",
            "manifest",
        }
        stages = [e for e in events.events if e["event"] == "ocr_stage_finished"]
        assert {e["stage"] for e in stages} >= {
            "dispatch",
            "authorize",
            "resolve_model",
            "load_revision",
            "render",
            "provider_preflight",
            "ocr_page",
            "parse_page",
            "store_artifact",
            "assemble",
            "read_artifact",
        }, "The real worker/API do not expose stage observations"
        for event in stages:
            assert event["run_id"] == run["id"]
            assert event["revision_id"] == revision["id"]
            assert event["source_sha256"] == revision["sha256"]
            assert event["duration_ms"] >= 0
            assert event["status"] == "completed"
        provider_events = [e for e in stages if e["stage"] == "ocr_page"]
        assert provider_events and provider_events[0]["provider_id"] == provider["id"]
        assert provider_events[0]["model_name"] == provider["model_name"]
        serialized = json.dumps(stages, ensure_ascii=False)
        for private in ("nemotron-test-secret", "Chỉ tiêu tuyển sinh", "data:image", fake.base_url):
            assert private not in serialized


@pytest.mark.parametrize("mode", ["ok", "invalid_layout", "truncated", "malformed"])
def test_raw_api_returns_original_bytes_even_when_processing_fails(client, mode):
    with FakeNemotron() as fake:
        fake.mode = mode
        run, url, _revision, _provider = prepare(client, fake, f"raw-api-{mode}")
        outcome = execute_now(client, run["id"])
        assert outcome.status == ("completed" if mode == "ok" else "failed")
        raw = client.get(url + "/pages/1/raw")
        assert raw.status_code == 200, "Raw evidence needs an authorized API read path"
        assert raw.content == fake._respond(0)[1]
        assert raw.headers["etag"].strip('"') == hashlib.sha256(raw.content).hexdigest()
        assert raw.headers["cache-control"] == "private, no-store"
        assert client.get(url + "/pages/999/raw").status_code == 404
        as_actor(None)
        assert client.get(url + "/pages/1/raw").status_code == 401
        as_actor(EDITOR)
        wrong_revision = url.replace(run["revision_id"], "rev-does-not-exist")
        assert client.get(wrong_revision + "/pages/1/raw").status_code == 404
        as_actor(OUTSIDER)
        # Workspace access intentionally hides resources from non-members.
        assert client.get(url + "/pages/1/raw").status_code == 404


def test_failed_layout_has_failed_parse_but_successful_raw_storage(client, monkeypatch):
    events = RecordedEvents()
    monkeypatch.setattr(execution, "logger", events)
    with FakeNemotron() as fake:
        fake.mode = "invalid_layout"
        run, _url, _revision, _provider = prepare(client, fake, "trace-layout-failure")
        assert execute_now(client, run["id"]).status == "failed"
        finished = [e for e in events.events if e["event"] == "ocr_stage_finished"]
        assert any(e["stage"] == "parse_page" and e["status"] == "failed" for e in finished)
        assert any(
            e["stage"] == "store_artifact"
            and e.get("artifact_kind") == "raw_response"
            and e["status"] == "completed"
            for e in finished
        )
        assert any(e["stage"] == "assemble" and e["status"] == "failed" for e in finished)


def test_usage_reservation_is_observable_without_monthly_limit(client, monkeypatch):
    events = RecordedEvents()
    monkeypatch.setattr(execution, "logger", events)
    with FakeNemotron() as fake:
        run, _url, _revision, _provider = prepare(client, fake, "trace-quota", quota=0)
        assert execute_now(client, run["id"]).status == "completed"
        assert fake.requests
        stages = [e for e in events.events if e["event"] == "ocr_stage_finished"]
        assert any(e["stage"] == "reserve_usage" and e["status"] == "completed" for e in stages)
