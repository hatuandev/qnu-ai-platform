"""Vietnamese NLP & Search Stopwords Manager — Dynamic Loading & Domain Suppression.

Provides unified, configurable stopword loading from external configuration files
and dynamic domain stopword suppression based on collection metadata.
"""

from __future__ import annotations

import functools
import logging
import os
import re
from pathlib import Path

from app.core.paths import get_configs_dir

logger = logging.getLogger(__name__)

# Minimal hardcoded fallback set in case external filesystem files are missing/unreadable
_EMERGENCY_FALLBACK_STOPWORDS: frozenset[str] = frozenset(
    {
        "và", "của", "cho", "với", "là", "có", "không", "để", "trong", "được",
        "những", "các", "này", "kia", "đó", "theo", "nào", "như", "thế", "một",
        "cần", "biết", "bao", "nhiêu", "về", "việc", "sang", "số", "cách", "thực",
        "hiện", "nhung", "tôi", "bạn", "trường", "đại", "học", "quy", "nhơn",
        "đhqn", "tb", "thông", "báo", "tổ", "hợp", "môn", "xét", "tuyển", "ngành",
    }
)


def _resolve_stopwords_filepath(custom_path: Path | str | None = None) -> Path | None:
    """Resolve the best candidate path for the stopwords dictionary file."""
    if custom_path:
        p = Path(custom_path).resolve()
        if p.is_file():
            return p

    # 1. Environment variable override
    env_file = os.environ.get("STOPWORDS_FILE")
    if env_file:
        p = Path(env_file).resolve()
        if p.is_file():
            return p

    # 2. Project configs directory (configs/stopwords_vi.txt)
    try:
        cfg_file = get_configs_dir() / "stopwords_vi.txt"
        if cfg_file.is_file():
            return cfg_file
    except Exception as exc:
        logger.debug("Failed resolving configs dir for stopwords: %s", exc)

    # 3. Core package resource directory (backend/app/core/resources/stopwords_vi.txt)
    pkg_res = Path(__file__).parent / "resources" / "stopwords_vi.txt"
    if pkg_res.is_file():
        return pkg_res.resolve()

    return None


@functools.lru_cache(maxsize=1)
def get_vietnamese_stopwords() -> frozenset[str]:
    """Load Vietnamese stopwords from external resource file with LRU caching.

    Reads lines from the configured UTF-8 text file, ignores comments (#) and empty lines.
    Falls back to emergency minimal set if file resolution fails.
    """
    file_path = _resolve_stopwords_filepath()
    if not file_path:
        logger.warning(
            "stopwords_vi.txt not found in configs or resources. Using emergency fallback stopwords."
        )
        return _EMERGENCY_FALLBACK_STOPWORDS

    try:
        content = file_path.read_text(encoding="utf-8")
        words: set[str] = set()
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            words.add(line.lower())

        if words:
            logger.debug("Loaded %d stopwords from %s", len(words), file_path)
            return frozenset(words)
    except Exception as exc:
        logger.error("Error reading stopwords file at %s: %s. Using emergency fallback.", file_path, exc)

    return _EMERGENCY_FALLBACK_STOPWORDS


def reload_stopwords() -> frozenset[str]:
    """Clear LRU cache and reload stopwords from disk."""
    get_vietnamese_stopwords.cache_clear()
    return get_vietnamese_stopwords()


def extract_collection_domain_stopwords(collection_name: str | None) -> set[str]:
    """Dynamically derive high-frequency collection domain stopwords from collection name.

    If a collection is named 'Thông tin tuyển sinh Đại học Quy Nhơn', words in the title
    appear across nearly 100% of the collection's chunks (DF ≈ 1.0).
    Extracting and suppressing them prevents search dilution without any hardcoded dictionary.
    """
    if not collection_name:
        return set()

    words = re.findall(r"[A-Za-zÀ-ỹ0-9]+", collection_name.lower())
    # Return syllables of length >= 2
    return {w for w in words if len(w) >= 2}


def is_stopword(token: str, extra_stopwords: set[str] | frozenset[str] | None = None) -> bool:
    """Check if a token is a stopword."""
    t = token.lower()
    if t in get_vietnamese_stopwords():
        return True
    return bool(extra_stopwords and t in extra_stopwords)
