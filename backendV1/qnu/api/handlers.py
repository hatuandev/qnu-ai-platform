"""Translate exceptions into RFC 7807 problem details."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from qnu.contracts.problem import ProblemDetail, problem_type
from qnu.platform.config import get_settings
from qnu.platform.correlation import current_correlation_id
from qnu.platform.errors import AppException
from qnu.platform.redaction import redact


def _is_gateway(request: Request) -> bool:
    return request.url.path.startswith(get_settings().API_PREFIX + "/integrations/openai/v1/")


def _openai_response(
    status: int, message: str, code: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        headers={**(headers or {}), "Cache-Control": "no-store"},
        content={
            "error": {
                "message": redact(message)
                if status < 500
                else "Dịch vụ chưa thể hoàn tất yêu cầu.",
                "type": "invalid_request_error" if status < 500 else "api_error",
                "param": None,
                "code": code,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        if _is_gateway(_):
            detail = exc.detail
            if isinstance(detail, dict) and "error" in detail:
                return _openai_response(
                    exc.status_code,
                    detail["error"]["message"],
                    detail["error"]["code"],
                    exc.headers,
                )
            return _openai_response(exc.status_code, str(detail), "invalid_request", exc.headers)
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
        )

    @app.exception_handler(AppException)
    async def _app_exception(_: Request, exc: AppException) -> JSONResponse:
        if _is_gateway(_):
            return _openai_response(exc.status_code, exc.detail, exc.code)
        issues = getattr(exc, "validation_issues", None)
        problem = ProblemDetail(
            type=problem_type(exc.code),
            title=exc.title,
            status=exc.status_code,
            detail=redact(exc.detail),
            code=exc.code,
            correlation_id=current_correlation_id(),
            errors=(
                {
                    "validation": [
                        f"{'.'.join(str(part) for part in item.get('path', []))}:"
                        f"{item.get('type', '')}"
                        for item in issues[:20]
                    ]
                }
                if issues
                else None
            ),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=problem.model_dump(),
            media_type="application/problem+json",
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        if _is_gateway(_):
            return _openai_response(409, "Dữ liệu đã thay đổi.", "data_conflict")
        problem = ProblemDetail(
            type=problem_type("data_conflict"),
            title="Dữ liệu xung đột",
            status=409,
            detail="Dữ liệu đã thay đổi hoặc vi phạm ràng buộc.",
            code="data_conflict",
            correlation_id=current_correlation_id(),
        )
        return JSONResponse(
            status_code=409, content=problem.model_dump(), media_type="application/problem+json"
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        if _is_gateway(_):
            return _openai_response(
                400, "Body hoặc tham số không được hỗ trợ/không đúng định dạng.", "invalid_request"
            )
        problem = ProblemDetail(
            type=problem_type("validation_error"),
            title="Dữ liệu không hợp lệ",
            status=422,
            detail="Một hoặc nhiều trường không đúng định dạng.",
            code="validation_error",
            correlation_id=current_correlation_id(),
        )
        return JSONResponse(
            status_code=422,
            content=problem.model_dump(),
            media_type="application/problem+json",
        )
