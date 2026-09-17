"""Tests for the Core document taxonomy contract."""

from __future__ import annotations

import pytest

from app.core.exceptions import AppException
from app.modules.document_types.catalog import (
    CATEGORY_NAMES,
    DOCUMENT_TYPE_CATALOG,
    ND30_CODES,
    document_type_source_hash,
    get_document_type_label,
    normalize_document_type_code,
)
from app.modules.document_types.schemas import DocumentTypeCreateRequest
from app.modules.document_types.seed_data import (
    DOCUMENT_TYPE_SEED_DATA,
    DOCUMENT_TYPE_SEED_VERSION,
)
from app.modules.tools.builtin.document_exporter import DocumentExporterTool
from app.modules.workflows.nodes.base import WorkflowContext
from app.modules.workflows.nodes.extract_fields_node import ExtractFieldsNodeHandler
from app.modules.workflows.schemas import WorkflowNodeSpec


def test_core_taxonomy_contains_37_types_and_28_nd30_codes() -> None:
    assert len(DOCUMENT_TYPE_CATALOG) == 37
    assert len(ND30_CODES) == 28
    assert set(CATEGORY_NAMES) == {"legal_internal", "administrative", "academic", "forms"}
    catalog_codes = {entry["code"] for entry in DOCUMENT_TYPE_CATALOG}
    assert all(code in catalog_codes for code in ND30_CODES)


def test_platform_seed_manifest_preserves_core_taxonomy() -> None:
    assert DOCUMENT_TYPE_SEED_VERSION == "qnu-document-taxonomy.v1"
    assert len(DOCUMENT_TYPE_SEED_DATA) == len(DOCUMENT_TYPE_CATALOG) == 37
    assert {item["code"] for item in DOCUMENT_TYPE_SEED_DATA} == {
        item["code"] for item in DOCUMENT_TYPE_CATALOG
    }
    assert all(item["source_system"] == "qnu-ai-core" for item in DOCUMENT_TYPE_SEED_DATA)
    assert all(item["is_system_default"] and not item["is_custom"] for item in DOCUMENT_TYPE_SEED_DATA)


def test_taxonomy_normalizes_core_labels_and_legacy_values() -> None:
    assert normalize_document_type_code("QUYẾT ĐỊNH") == "quyet_dinh"
    assert normalize_document_type_code("decision") == "quyet_dinh"
    assert normalize_document_type_code("official_dispatch") == "cong_van"
    assert normalize_document_type_code("  thông báo  ") == "thong_bao"
    assert normalize_document_type_code("unknown_type") is None
    assert get_document_type_label("to_trinh") == "Tờ trình"


def test_taxonomy_source_hash_is_stable_and_utf8() -> None:
    source_hash = document_type_source_hash()
    assert len(source_hash) == 64
    assert source_hash == document_type_source_hash()


def test_custom_document_type_request_rejects_non_canonical_code_shape() -> None:
    with pytest.raises(ValueError):
        DocumentTypeCreateRequest(
            code="Quyết Định",
            name="Loại không hợp lệ",
            category="administrative",
        )


@pytest.mark.asyncio
async def test_extract_fields_emits_canonical_code_without_fake_general_type() -> None:
    handler = ExtractFieldsNodeHandler()
    context = WorkflowContext(
        workflow_id="drafting-assistant",
        tenant_id="tenant_qnu",
        conversation_id=None,
        inputs={"message": "Soạn Quyết định về việc thành lập hội đồng."},
    )
    result = await handler.execute(
        WorkflowNodeSpec(id="extract", type="extract.fields"),
        context,
    )
    fields = result.output["extracted_fields"]
    assert fields["document_type_code"] == "quyet_dinh"
    assert fields["doc_type"] == "quyet_dinh"
    assert fields["document_type_status"] == "classified"


@pytest.mark.asyncio
async def test_document_exporter_rejects_unknown_document_type(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.modules.tools.builtin.document_exporter.settings.LOCAL_STORAGE_PATH", str(tmp_path))
    with pytest.raises(AppException) as error:
        await DocumentExporterTool().execute(
            {"document_type": "not_a_document_type", "title": "Test", "body_paragraphs": []}
        )
    assert error.value.code == "document_type_invalid"
