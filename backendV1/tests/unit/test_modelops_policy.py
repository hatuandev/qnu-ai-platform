"""Pure ModelOps policy: masking, capabilities, endpoint safety and ownership."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qnu.domains.modelops.keys.service import mask_secret
from qnu.domains.modelops.schemas import (
    AllowlistUpdateRequest,
    KeyCreateRequest,
    ProviderCreateRequest,
)
from qnu.platform.errors import AppException
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.platform.ownership import LEGACY_TABLES


def test_secret_is_masked_to_last_four_characters() -> None:
    assert mask_secret("sk-live-abcdef123456") == "****3456"
    assert mask_secret("abc") == "****"


def test_key_secret_is_not_exposed_in_repr() -> None:
    request = KeyCreateRequest(name="primary", secret="sk-super-secret-value")
    assert "sk-super-secret-value" not in repr(request)


def test_provider_capabilities_must_be_unique_and_known() -> None:
    with pytest.raises(ValidationError):
        ProviderCreateRequest(
            name="p1",
            provider_type="openai_compatible",
            base_url="https://example.test/v1",
            model_name="m",
            capabilities=["chat", "chat"],
        )
    with pytest.raises(ValidationError):
        ProviderCreateRequest(
            name="p1",
            provider_type="openai_compatible",
            base_url="https://example.test/v1",
            model_name="m",
            capabilities=["vision"],
        )


def test_workspace_allowlist_rejects_duplicates() -> None:
    with pytest.raises(ValidationError):
        AllowlistUpdateRequest(provider_ids=["prv_1", "prv_1"])


def test_endpoint_policy_blocks_metadata_and_bad_schemes() -> None:
    with pytest.raises(AppException):
        assert_allowed_endpoint("ftp://example.test/v1", allow_private=True)
    with pytest.raises(AppException):
        assert_allowed_endpoint("http://169.254.169.254/latest", allow_private=True)
    assert assert_allowed_endpoint("http://localhost:11434/v1", allow_private=True)


def test_modelops_tables_never_collide_with_legacy_names() -> None:
    from qnu.domains.modelops.models import Base

    v1_tables = set(Base.metadata.tables)
    assert {
        "providers",
        "provider_keys",
        "provider_key_audits",
        "model_defaults",
        "workspace_allowed_providers",
    } <= v1_tables
    assert not (v1_tables & LEGACY_TABLES)


@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@example.test/v1",
        "https://example.test/v1?api_key=anything",
        "http://[::]/v1",
        "http://169.254.1.2/v1",
    ],
)
def test_endpoint_never_carries_credentials_or_metadata_addresses(url):
    with pytest.raises(AppException):
        assert_allowed_endpoint(url, allow_private=True)


def test_structured_logging_redacts_key_and_prompt_fields():
    from qnu.platform.logging import _redact_event

    result = _redact_event(
        None,
        "info",
        {
            "secret": "any-format-credential",
            "message": "sk_live_testcredential123456",
            "nested": {"prompt": "private document"},
        },
    )
    assert result["secret"] == "[REDACTED]"
    assert "testcredential" not in result["message"]
    assert result["nested"]["prompt"] == "[REDACTED]"
