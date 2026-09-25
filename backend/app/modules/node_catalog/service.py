"""Async loader for the versioned NodeManifest catalog."""

from __future__ import annotations

import asyncio
import json
import logging
import unicodedata
from pathlib import Path
from typing import Any

from app.modules.node_catalog.models import NodeManifestRecord
from app.modules.node_catalog.schemas import NodeManifestResponse

logger = logging.getLogger(__name__)


def _normalize_text(value: object, field_name: str, source_file: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Manifest field '{field_name}' is required")
    return unicodedata.normalize("NFC", value.strip())


def _mapping(value: object, field_name: str, source_file: Path) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"Manifest field '{field_name}' must be an object")
    return value


def _parse_manifest(raw_data: object, source_file: Path) -> NodeManifestRecord:
    if not isinstance(raw_data, dict):
        raise TypeError("Manifest root must be an object")

    metadata = _mapping(raw_data.get("metadata"), "metadata", source_file)
    spec = _mapping(raw_data.get("spec"), "spec", source_file)
    compatibility = _mapping(spec.get("compatibility"), "spec.compatibility", source_file)

    return NodeManifestRecord(
        api_version=_normalize_text(raw_data.get("api_version"), "api_version", source_file),
        type=_normalize_text(metadata.get("type"), "metadata.type", source_file),
        version=_normalize_text(metadata.get("version"), "metadata.version", source_file),
        display_name=_normalize_text(
            metadata.get("display_name"), "metadata.display_name", source_file
        ),
        description=_normalize_text(
            metadata.get("description"), "metadata.description", source_file
        ),
        category=_normalize_text(metadata.get("category"), "metadata.category", source_file),
        status=_normalize_text(
            compatibility.get("status", "active"), "spec.compatibility.status", source_file
        ),
        input_schema=_mapping(spec.get("input_schema"), "spec.input_schema", source_file),
        output_schema=_mapping(spec.get("output_schema"), "spec.output_schema", source_file),
        config_schema=_mapping(spec.get("config_schema"), "spec.config_schema", source_file),
    )


def _load_manifest_file(source_file: Path) -> NodeManifestRecord | None:
    try:
        with source_file.open(encoding="utf-8") as manifest_file:
            raw_data = json.load(manifest_file)
        return _parse_manifest(raw_data, source_file)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Skipping invalid node manifest path=%s error=%s", source_file, exc)
        return None


def _to_response(record: NodeManifestRecord) -> NodeManifestResponse:
    return NodeManifestResponse(
        api_version=record.api_version,
        type=record.type,
        version=record.version,
        display_name=record.display_name,
        description=record.description,
        category=record.category,
        status=record.status,
        input_schema=record.input_schema,
        output_schema=record.output_schema,
        config_schema=record.config_schema,
    )


class NodeCatalogService:
    """Discover approved Core manifests without depending on a database seed."""

    def __init__(self, nodes_dir: Path | None = None) -> None:
        from app.core.paths import get_configs_dir

        self.nodes_dir = nodes_dir or (get_configs_dir() / "nodes")

    async def list_nodes(
        self,
        search: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[NodeManifestResponse]:
        """Load and filter manifests deterministically from the checked-in catalog."""
        if not self.nodes_dir.is_dir():
            logger.warning("Node catalog directory does not exist path=%s", self.nodes_dir)
            return []

        manifest_paths = sorted(self.nodes_dir.glob("*.json"))
        records = await asyncio.gather(
            *(asyncio.to_thread(_load_manifest_file, path) for path in manifest_paths)
        )
        valid_records = [record for record in records if record is not None]

        normalized_search = _normalize_filter(search)
        normalized_category = _normalize_filter(category)
        normalized_status = _normalize_filter(status)

        filtered_records = [
            record
            for record in valid_records
            if _matches_filters(record, normalized_search, normalized_category, normalized_status)
        ]
        filtered_records.sort(key=lambda record: (record.category, record.display_name, record.type))
        return [_to_response(record) for record in filtered_records]

    def get_manifests_map(self) -> dict[str, NodeManifestRecord]:
        """Return a mapping of node_type -> NodeManifestRecord for synchronous runtime validation."""
        if not self.nodes_dir.is_dir():
            return {}
        manifest_paths = sorted(self.nodes_dir.glob("*.json"))
        records: dict[str, NodeManifestRecord] = {}
        for path in manifest_paths:
            rec = _load_manifest_file(path)
            if rec:
                records[rec.type] = rec
        return records


def _normalize_filter(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return unicodedata.normalize("NFC", value.strip()).casefold()


def _matches_filters(
    record: NodeManifestRecord,
    search: str | None,
    category: str | None,
    status: str | None,
) -> bool:
    if category and record.category.casefold() != category:
        return False
    if status and record.status.casefold() != status:
        return False
    if not search:
        return True
    searchable = f"{record.type} {record.display_name} {record.description} {record.category}".casefold()
    return search in searchable


node_catalog_service = NodeCatalogService()
