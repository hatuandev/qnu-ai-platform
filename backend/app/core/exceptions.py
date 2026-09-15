"""Domain Exceptions & RFC 7807 Problem Details Exception Handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DomainException(Exception):
    """Base domain exception with standardized status code and error code."""

    def __init__(
        self,
        message: str | None = None,
        code: str = "domain_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
        title: str | None = None,
        detail: str | None = None,
    ):
        msg = message or detail or title or "Domain error"
        super().__init__(msg)
        self.message = msg
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.title = title or msg
        self.detail = detail or msg


AppException = DomainException


class EntityNotFoundError(DomainException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message, code="entity_not_found", status_code=status.HTTP_404_NOT_FOUND, details=details
        )


NotFoundException = EntityNotFoundError


class EntityAlreadyExistsError(DomainException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="entity_already_exists",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class AuthenticationError(DomainException):
    def __init__(
        self, message: str = "Chưa xác thực danh tính", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message,
            code="unauthenticated",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(DomainException):
    def __init__(
        self, message: str = "Không có quyền truy cập", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message, code="unauthorized", status_code=status.HTTP_403_FORBIDDEN, details=details
        )


class RateLimitExceededError(DomainException):
    def __init__(
        self,
        message: str = "Vượt quá giới hạn tần suất yêu cầu",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers adhering to RFC 7807 Problem Details specification."""

    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://errors.qnu.ai/{exc.code}",
                "title": exc.message,
                "status": exc.status_code,
                "detail": exc.message,
                "code": exc.code,
                "instance": request.url.path,
                "details": exc.details,
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "type": "https://errors.qnu.ai/validation-error",
                "title": "Dữ liệu yêu cầu không hợp lệ",
                "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "detail": str(exc),
                "code": "validation_error",
                "instance": request.url.path,
                "errors": exc.errors(),
                "correlation_id": correlation_id,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        detail_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "https://errors.qnu.ai/http-error",
                "title": detail_msg,
                "status": exc.status_code,
                "detail": detail_msg,
                "code": "http_error",
                "instance": request.url.path,
                "correlation_id": correlation_id,
            },
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.error(
            "Unhandled internal server error [corr=%s]: %s", correlation_id, exc, exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "type": "https://errors.qnu.ai/internal-server-error",
                "title": "Lỗi máy chủ nội bộ",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "detail": "Đã xảy ra sự cố nội bộ. Vui lòng thử lại sau hoặc liên hệ quản trị viên.",
                "code": "internal_error",
                "instance": request.url.path,
                "correlation_id": correlation_id,
            },
        )
