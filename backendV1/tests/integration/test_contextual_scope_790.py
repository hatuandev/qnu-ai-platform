"""API authorization, sealed recipes and before-TopK scope on isolated providers."""

import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.domains.knowledge.index.presentation import reading_text
from qnu.domains.knowledge.index.schemas import SearchHit
from qnu.platform.database import AsyncSessionFactory
from tests.integration.knowledge_support import OUTSIDER, PLATFORM, as_actor
from tests.integration.rag_support_672 import metadata_index as metadata_index_fixture
from tests.integration.rag_support_672 import prepared, register

metadata_index = metadata_index_fixture


@pytest.fixture
def explicit_definition(monkeypatch):
    from tests.integration import compiler_support

    monkeypatch.setattr(
        compiler_support,
        "TABLE_RESPONSE",
        compiler_support.TABLE_RESPONSE.replace("PHỤ LỤC 01", "Hải dương học (HDH)"),
    )


def test_registration_rejects_same_file_wrong_unit_without_creating_a_version(client):
    data = prepared(client)
    changed = copy.deepcopy(data["annotations"])
    # Fourth paragraph has not cited either of the source year cells.
    changed[0]["target"] = "paragraph:0:3"
    invalid = register(client, data, changed, key="wrong-unit")
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["code"] == "retrieval_metadata_invalid"
    valid = register(client, data, key="wrong-unit")
    assert valid.status_code == 201, valid.text


@pytest.mark.parametrize("metadata_index", [True], indirect=True)
def test_new_recipe_preserves_body_and_scope_before_topk(client, metadata_index):
    data = metadata_index

    async def read_chunks():
        async with AsyncSessionFactory() as db:
            run = await db.get(IndexRun, data["index_run_id"])
            rows = list(await db.scalars(select(IndexChunk).where(IndexChunk.run_id == run.id)))
            return run.config, {r.id: r for r in rows}

    config, chunks = client.portal.call(read_chunks)
    assert config["search_context_version"] == "qnu.search-context/v1"
    assert all(c.structure["search_context"]["original_text"] for c in chunks.values())
    comparisons = []
    for mode in ("dense", "hybrid"):
        found = client.post(
            data["base"] + "/search",
            json={
                "query": "Nguồn dữ liệu năm 2024",
                "scope_resolution": "catalog",
                "mode": mode,
                "top_k": 1,
            },
        )
        assert found.status_code == 200, found.text
        result = found.json()
        assert result["trace"]["scope_resolution"]["filters"] == [{"data_year": 2024}]
        assert result["trace"]["metadata_eligible_chunks"] == 2
        hit = SearchHit.model_validate(result["hits"][0])
        assert not reading_text(hit).startswith('{"version":')
        assert hit.structure["retrieval_metadata"][0]["values"]["data_year"] == 2024
        comparisons.append(
            {
                "mode": mode,
                "scope": result["trace"]["scope_resolution"],
                "ids": [h["chunk_id"] for h in result["hits"]],
            }
        )
    count = len(data["embedding"].requests)
    unknown = client.post(
        data["base"] + "/search",
        json={
            "query": "Nguồn năm 2099",
            "scope_resolution": "catalog",
            "mode": "dense",
        },
    )
    assert unknown.status_code == 200 and unknown.json()["hits"] == []
    assert unknown.json()["trace"]["scope_resolution"]["filters"] == [{"data_year": 2099}]
    assert len(data["embedding"].requests) == count  # No retry and no unfiltered fallback.
    # Both data years occur within one published version and can be read together.
    overview = client.post(
        data["base"] + "/search",
        json={
            "query": "Nguồn dữ liệu?",
            "scope_resolution": "catalog",
            "mode": "dense",
        },
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["trace"]["scope_resolution"]["filters"] == [{}]
    assert len(data["embedding"].requests) == count + 1

    count = len(data["embedding"].requests)
    conflict = client.post(
        data["base"] + "/search",
        json={
            "query": "Nguồn dữ liệu năm 2024",
            "scope_resolution": "catalog",
            "mode": "dense",
            "metadata_filter": {"data_year": 2023},
        },
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "answer_scope_conflict"
    assert len(data["embedding"].requests) == count
    artifact = Path("storage/context790/functional-comparison.json")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "kind": "controlled_functional_comparison",
                "quality_claim": False,
                "snapshot": data["index_run_id"],
                "comparisons": comparisons,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    as_actor(OUTSIDER)
    denied = client.post(
        data["base"] + "/search",
        json={
            "query": "Nguồn năm 2024",
            "scope_resolution": "catalog",
            "mode": "dense",
        },
    )
    assert denied.status_code in (403, 404)


@pytest.mark.usefixtures("explicit_definition")
@pytest.mark.parametrize("metadata_index", [True], indirect=True)
def test_glossary_uses_canonical_source_and_disappears_after_withdrawal(client, metadata_index):
    data = metadata_index
    result = client.post(
        data["base"] + "/search",
        json={
            "query": "HDH năm 2024",
            "scope_resolution": "catalog",
            "mode": "dense",
            "top_k": 1,
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["trace"]["scope_resolution"]["alias_count"] == 1
    request = data["embedding"].requests[-1]["body"]
    assert "Hải dương học" in str(request["input"])
    as_actor(PLATFORM)
    preview = client.post(
        data["version_url"] + "/decision-preview",
        json={
            "action": "withdraw",
            "reason": "Scope withdrawal regression.",
        },
    )
    assert preview.status_code == 200, preview.text
    withdrawn = client.post(
        data["version_url"] + "/decisions",
        headers={
            "Idempotency-Key": "withdraw-context790",
        },
        json={
            "preview_id": preview.json()["id"],
            "preview_sha256": preview.json()["preview_sha256"],
        },
    )
    assert withdrawn.status_code == 200, withdrawn.text
    count = len(data["embedding"].requests)
    empty = client.post(
        data["base"] + "/search",
        json={
            "query": "HDH năm 2024",
            "scope_resolution": "catalog",
            "mode": "dense",
        },
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["status"] == "no_eligible_content" and not empty.json()["hits"]
    assert len(data["embedding"].requests) == count


@pytest.mark.parametrize("metadata_index", [True], indirect=True)
def test_catalog_checks_manifest_before_planning_or_embedding(client, metadata_index):
    data = metadata_index

    async def tamper():
        async with AsyncSessionFactory() as db:
            row = await db.scalar(
                select(IndexChunk).where(IndexChunk.run_id == data["index_run_id"])
            )
            structure = copy.deepcopy(row.structure)
            structure["retrieval_metadata"] = [
                {"target": "document", "values": {"data_year": 2099}}
            ]
            row.structure = structure
            await db.commit()

    client.portal.call(tamper)
    count = len(data["embedding"].requests)
    result = client.post(
        data["base"] + "/search",
        json={
            "query": "Nguồn năm 2099",
            "scope_resolution": "catalog",
            "mode": "dense",
        },
    )
    assert result.status_code == 409, result.text
    assert result.json()["code"] == "index_metadata_changed"
    assert len(data["embedding"].requests) == count
