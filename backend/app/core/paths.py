"""Filesystem Paths and Configuration Resolution for QNU AI Platform.

Ensures reliable resolution of project configs (workflows, nodes, modules)
across local development on Windows/Linux host, Docker containers, and custom paths.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_configs_dir() -> Path:
    """Resolve the directory containing platform configurations.

    Priority order:
    1. CONFIGS_DIR environment variable (if set and exists)
    2. /app/configs (Standard container path inside Docker)
    3. Traversal up the directory hierarchy looking for configs/workflows
    4. Fallback: 4 levels up from this file + configs
    """
    # 1. Environment variable override
    env_dir = os.environ.get("CONFIGS_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        if p.is_dir():
            return p

    # 2. Standard Docker container path
    container_configs = Path("/app/configs")
    if container_configs.is_dir() and (container_configs / "workflows").is_dir():
        return container_configs.resolve()

    # 3. Dynamic upward search from current file location
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "configs"
        if candidate.is_dir() and (candidate / "workflows").is_dir():
            return candidate.resolve()

    # 4. Fallback relative to repository layout
    fallback = current.parents[4] / "configs"
    return fallback.resolve()
