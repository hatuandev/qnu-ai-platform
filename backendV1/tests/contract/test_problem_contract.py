"""Problem detail contract stays RFC 7807-compatible."""

from __future__ import annotations

from qnu.contracts.problem import ProblemDetail, problem_type


def test_problem_type_uses_error_base_url() -> None:
    assert problem_type("forbidden") == "https://errors.qnu.edu.vn/forbidden"


def test_problem_payload_has_required_fields() -> None:
    payload = ProblemDetail(
        type=problem_type("invalid_token"),
        title="Phiên không hợp lệ",
        status=401,
        detail="Token hết hạn",
        code="invalid_token",
    ).model_dump()
    assert payload["status"] == 401
    assert payload["type"].endswith("invalid_token")
