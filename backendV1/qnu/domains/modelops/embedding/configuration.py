"""Dimension declarations are bound to endpoint/model, never a global vector-size default."""

from qnu.domains.modelops.models import Provider

KEY = "embedding_dimension_v1"


def set_dimension(provider: Provider, dimension: int | None) -> None:
    extra = dict(provider.extra_config or {})
    if dimension is None:
        extra.pop(KEY, None)
    else:
        extra[KEY] = {
            "endpoint": provider.base_url.rstrip("/"),
            "model": provider.model_name,
            "dimension": dimension,
            "basis": "operator_configured",
        }
    provider.extra_config = extra


def read_dimension(provider: Provider) -> tuple[int | None, str]:
    value = (provider.extra_config or {}).get(KEY)
    if not isinstance(value, dict):
        return None, "unknown"
    if (
        value.get("endpoint") != provider.base_url.rstrip("/")
        or value.get("model") != provider.model_name
    ):
        return None, "stale"
    dim = value.get("dimension")
    return (dim, "configured") if type(dim) is int and 0 < dim <= 65536 else (None, "unknown")
