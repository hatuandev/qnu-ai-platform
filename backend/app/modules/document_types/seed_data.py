"""Versioned Platform seed rows derived from the qnu-ai-core taxonomy."""

from __future__ import annotations

from typing import TypedDict

from app.modules.document_types.catalog import DOCUMENT_TYPE_CATALOG, ND30_CODES


class DocumentTypeSeedDefinition(TypedDict):
    """Operational seed row generated from one Core taxonomy definition."""

    code: str
    name: str
    category: str
    description: str
    priority: int
    retention_period: str
    nd30: bool
    is_active: bool
    is_system_default: bool
    is_custom: bool
    source_system: str


DOCUMENT_TYPE_SEED_VERSION = "qnu-document-taxonomy.v1"

# Keep Core's catalog as the single business-data source.  The additional
# fields here are Platform persistence defaults, not a second taxonomy.
DOCUMENT_TYPE_SEED_DATA: tuple[DocumentTypeSeedDefinition, ...] = tuple(
    {
        **definition,
        "nd30": definition["code"] in ND30_CODES,
        "is_active": True,
        "is_system_default": True,
        "is_custom": False,
        "source_system": "qnu-ai-core",
    }
    for definition in DOCUMENT_TYPE_CATALOG
)
