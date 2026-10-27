"""Translate exceptions into RFC 7807 problem details."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from qnu.contracts.problem import ProblemDetail, problem_type
from qnu.platform.correlation import current_correlation_id
from qnu.platform.errors import AppException
from qnu.platform.redaction import redact


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app_exception(_: Request, exc: AppException) -> JSONResponse:
        problem = ProblemDetail(
            type=problem_type(exc.code),
            title=exc.title,
            status=exc.status_code,
            detail=redact(exc.detail),
            code=exc.code,
            correlation_id=current_correlation_id(),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=problem.model_dump(),
            media_type="application/problem+json",
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
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
