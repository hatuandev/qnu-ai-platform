"""Pydantic DTOs for the Core-compatible node catalog endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NodeManifestResponse(BaseModel):
    """Node manifest metadata and schemas consumed by the Platform UI."""

    api_version: str = "qnu.ai/v1alpha1"
    type: str
    version: str
    display_name: str
    description: str
    category: str
    status: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    config_schema: dict[str, Any] = Field(default_factory=dict)


class NodeCatalogResponse(BaseModel):
    """Envelope kept compatible with qnu-ai-core ``GET /nodes``."""

    items: list[NodeManifestResponse]
