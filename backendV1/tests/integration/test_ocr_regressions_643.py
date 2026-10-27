"""Independent review probes: synthetic documents, loopback provider, disposable DB."""

import io
import json
import zipfile
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pymupdf
from sqlalchemy import select, update

from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.ocr.artifacts.render import render_document
from qnu.domains.ocr.config import processing_config
from qnu.domains.ocr.models import OcrProcessingRun, OcrRunArtifact, utcnow
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import AppException, DependencyUnavailable
from qnu.workers.tasks.ocr import ocr_reconcile_queued, shutdown
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    PLATFORM,
    as_actor,
    workspace_with_editor,
)
from tests.integration.ocr_support import (
    FakeJobQueue,
    FakeNemotron,
    execute_now,
    prepare_source,
    real_pdf,
    request_run,
    runs_url,
    setup_ocr_provider,
    use_queue,
)

observations = {}


def record(name, value):
    observations[name] = value
    (Path(get_settings().LOCAL_STORAGE_PATH).parent / "regressions643.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def setup(client, fake, code, *, pages=1):
    use_queue(FakeJobQueue())
    ws = workspace_with_editor(client, code)
    as_actor(EDITOR)
    col, source, revision = prepare_source(
        client, ws["id"], code, payload=real_pdf([f"Synthetic page {i}" for i in range(pages)])
    )
    provider = setup_ocr_provider(client, ws["id"], fake.base_url)
    as_actor(EDITOR)
    run = request_run(
        client, ws["id"], col["id"], source["id"], revision["id"], queue=FakeJobQueue()
    ).json()["run"]
    url = f"{runs_url(ws['id'], col['id'], source['id'], revision['id'])}/{run['id']}"
    return provider, run, url


def test_arq_worker_startup_accepts_the_context_arq_actually_supplies(client):
    from arq.worker import create_worker

    from qnu.workers.settings import WorkerSettings

    async def scenario():
        worker = create_worker(WorkerSettings, handle_signals=False)
        context = {**worker.ctx, "redis": object()}
        try:
            await worker.on_startup(context)
        except KeyError as exc:
            record("worker_startup", {"arq_context_keys": list(context), "missing": str(exc)})
            return str(exc)
        finally:
            if "container" in context:
                await shutdown(context)

    missing = client.portal.call(scenario)
    assert missing is None, f"Configured ARQ worker cannot start: missing {missing}"


def test_ocr_runtime_blocks_output_above_registered_model_capacity(client):
    with FakeNemotron() as fake:
        provider, run, _url = setup(client, fake, "review-capacity")
        as_actor(PLATFORM)
        response = client.patch(
            f"{API}/modelops/providers/{provider['id']}",
            json={"token_limits": {"context_window_tokens": 128, "max_output_tokens": 32}},
        )
        assert response.status_code == 200
        as_actor(EDITOR)
        outcome = execute_now(client, run["id"])
        record(
            "capacity",
            {
                "registered_output": 32,
                "status": outcome.status,
                "sent_outputs": [r["body"]["max_tokens"] for r in fake.requests],
            },
        )
        assert fake.requests == [], "OCR sent a request that exceeds registered output capacity"


def test_resumed_run_blocks_a_changed_endpoint_and_model(client, monkeypatch):
    with FakeNemotron() as old, FakeNemotron() as new:
        provider, run, url = setup(client, old, "review-pinning", pages=2)
        original_reserve = usage_service.reserve

        async def fail_before_second_call(*args, **kwargs):
            if args[4].endswith(":2"):
                raise DependencyUnavailable(
                    "Injected pre-request interruption", code="storage_unavailable"
                )
            return await original_reserve(*args, **kwargs)

        monkeypatch.setattr(usage_service, "reserve", fail_before_second_call)
        first = execute_now(client, run["id"])
        assert first.status == "queued" and len(old.requests) == 1
        monkeypatch.setattr(usage_service, "reserve", original_reserve)
        as_actor(PLATFORM)
        assert (
            client.patch(
                f"{API}/modelops/providers/{provider['id']}",
                json={"base_url": new.base_url, "model_name": "changed-model"},
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        second = execute_now(client, run["id"])
        detail = client.get(url).json()
        doc = client.get(url + "/document")
        record(
            "pinning",
            {
                "first": first.status,
                "second": second.status,
                "old_models": [r["body"]["model"] for r in old.requests],
                "new_models": [r["body"]["model"] for r in new.requests],
                "run_config_provider": detail["config"].get("provider")
                if "config" in detail
                else None,
                "canonical_provider": doc.json().get("processing", {}).get("provider")
                if doc.status_code == 200
                else None,
            },
        )
        assert new.requests == [] and second.status != "completed", (
            "One generation mixed OCR from different model/endpoint"
        )


def test_reconcile_requeues_an_expired_dispatched_worker_run(client):
    with FakeNemotron() as fake:
        _provider, run, url = setup(client, fake, "review-recover")
        queue = FakeJobQueue()

        async def scenario():
            async with AsyncSessionFactory() as db:
                await db.execute(
                    update(OcrProcessingRun)
                    .where(OcrProcessingRun.id == run["id"])
                    .values(
                        status="running",
                        worker_id="terminated-worker",
                        attempt_count=1,
                        lease_expires_at=utcnow() - timedelta(seconds=1),
                    )
                )
                await db.commit()
            count = await ocr_reconcile_queued({"container": SimpleNamespace(job_queue=queue)})
            return count

        count = client.portal.call(scenario)
        record(
            "recovery",
            {
                "requeued": count,
                "jobs": len(queue.jobs),
                "status": client.get(url).json()["status"],
            },
        )
        assert count == 1, "Expired dispatched run is never picked up by the only recovery cron"


def test_layout_failure_preserves_the_raw_provider_response(client):
    with FakeNemotron() as fake:
        fake.mode = "invalid_layout"
        _provider, run, _url = setup(client, fake, "review-raw")
        result = execute_now(client, run["id"])
        assert len(fake.requests) == 1 and result.status == "failed"

        async def kinds():
            async with AsyncSessionFactory() as db:
                return list(
                    (
                        await db.scalars(
                            select(OcrRunArtifact.kind).where(OcrRunArtifact.run_id == run["id"])
                        )
                    ).all()
                )

        artifacts = client.portal.call(kinds)
        record("raw_response", {"status": result.status, "artifacts": artifacts})
        assert "raw_response" in artifacts, (
            "Provider answer disappeared because layout parsing ran before raw persistence"
        )


def test_docx_header_is_preserved_or_reported_as_missing(client):
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    relations = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{namespace}" xmlns:r="{relations}"><w:body><w:p><w:r><w:t>BODY_TEXT</w:t></w:r></w:p><w:sectPr><w:headerReference w:type="default" r:id="rIdHeader"/></w:sectPr></w:body></w:document>',
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdHeader" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/></Relationships>',
        )
        archive.writestr(
            "word/header1.xml",
            f'<w:hdr xmlns:w="{namespace}"><w:p><w:r><w:t>HEADER_123_2026</w:t></w:r></w:p></w:hdr>',
        )
    try:
        rendered = render_document(buffer.getvalue(), ".docx", processing_config(get_settings()))
    except AppException as exc:
        assert exc.code == "docx_layout_unsupported"
        return
    with pymupdf.open(stream=rendered.fixed_layout_pdf, filetype="pdf") as document:
        text = "\n".join(page.get_text() for page in document)
    record("docx_header", {"rendered_text": text, "warnings": list(rendered.warnings)})
    assert "HEADER_123_2026" in text or any("header" in w for w in rendered.warnings), (
        "DOCX header disappeared without a warning before OCR"
    )
