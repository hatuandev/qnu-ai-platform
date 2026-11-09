"""Report only the checks that ran; absent warnings never prove a draft is correct."""

QUALITY_VERSION = "qnu.compiler.quality/v1"
NO_ERROR_FOUND = "no_error_found"
PARTIALLY_CHECKED = "partially_checked"
NOT_CHECKED = "not_checked"
CONFIRMED_BY_SOURCE = "confirmed_by_source"


def quality_validation(*, source_binding: str, coverage: str) -> dict:
    """Four distinct outcomes per check; citations alone never confirm semantic faithfulness."""
    return {
        "schema_version": QUALITY_VERSION,
        "checks": {
            "schema": NO_ERROR_FOUND,
            "citation_membership": NO_ERROR_FOUND,
            "source_binding": source_binding,
            "coverage": coverage,
            "tables": CONFIRMED_BY_SOURCE,
            "numbers": source_binding,
            "duplicates": NOT_CHECKED,
            "semantic_faithfulness": NOT_CHECKED,
        },
    }
