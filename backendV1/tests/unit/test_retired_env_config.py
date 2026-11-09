"""Retired env knobs must not return as runtime configuration."""

from qnu.platform.config import Settings

RETIRED = (
    "COMPILER_MAX_OUTPUT_TOKENS",
    "RAG_MAX_OUTPUT_TOKENS",
    "CONVERSATION_REWRITE_MAX_OUTPUT_TOKENS",
    "QDRANT_COLLECTION",
    "VECTOR_SIZE",
)


def test_old_deployment_env_values_are_ignored(monkeypatch):
    for name in RETIRED:
        monkeypatch.setenv(name, "1")
    settings = Settings(_env_file=None)
    for name in RETIRED:
        assert not hasattr(settings, name)
    # The only remaining output override is the explicit legacy image-OCR one.
    assert settings.OCR_MAX_OUTPUT_TOKENS is None
