from app.modules.modelops.models import ProviderApiKey
from app.modules.modelops.services.key_monitoring_service import key_monitoring_service
from app.modules.modelops.services.key_status import normalize_provider_key_status
from app.modules.modelops.services.provider_key_rotation_service import (
    provider_key_rotation_service,
)
from app.modules.modelops.services.provider_service import _sanitize_key_for_output


def test_legacy_disabled_status_is_normalized_at_every_output_boundary() -> None:
    assert normalize_provider_key_status("disabled") == "inactive"
    assert _sanitize_key_for_output({"id": "key-1", "status": "disabled"})[
        "status"
    ] == "inactive"

    key = ProviderApiKey(
        id="key-1",
        provider_id="provider-1",
        name="Legacy key",
        api_key_encrypted="secret",
        api_key_masked="masked",
        status="disabled",
        is_active=False,
    )
    assert provider_key_rotation_service.to_public_dict(key)["status"] == "inactive"


def test_unknown_status_fails_closed_and_is_not_available_for_rotation() -> None:
    assert normalize_provider_key_status("unexpected-state") == "inactive"
    preview = key_monitoring_service.preview(
        [{"id": "key-1", "name": "Unknown", "status": "unexpected-state"}]
    )
    assert preview["key_order"] == []
    assert preview["rotated"] is False
