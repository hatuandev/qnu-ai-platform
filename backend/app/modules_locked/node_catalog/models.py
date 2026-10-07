"""Domain model for a validated QNU Core node manifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NodeManifestRecord:
    """Immutable catalog item loaded from a versioned Core manifest file."""

    api_version: str
    type: str
    version: str
    display_name: str
    description: str
    category: str
    status: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    config_schema: dict[str, Any]
