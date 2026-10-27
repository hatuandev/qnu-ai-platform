"""Application errors that map to RFC 7807 problem details."""

from __future__ import annotations


class AppException(Exception):
    """Domain/HTTP error carrying a stable machine code."""

    def __init__(
        self,
        detail: str,
        *,
        code: str,
        status_code: int = 400,
        title: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code
        self.title = title or "Yêu cầu không hợp lệ"


class EntityNotFound(AppException):
    def __init__(self, detail: str, *, code: str = "not_found") -> None:
        super().__init__(detail, code=code, status_code=404, title="Không tìm thấy")


class Conflict(AppException):
    def __init__(self, detail: str, *, code: str = "conflict") -> None:
        super().__init__(detail, code=code, status_code=409, title="Xung đột dữ liệu")


class Forbidden(AppException):
    def __init__(self, detail: str, *, code: str = "forbidden") -> None:
        super().__init__(detail, code=code, status_code=403, title="Không có quyền")


class PayloadTooLarge(AppException):
    def __init__(self, detail: str, *, code: str = "payload_too_large") -> None:
        super().__init__(detail, code=code, status_code=413, title="Tệp quá lớn")


class UnsupportedMedia(AppException):
    def __init__(self, detail: str, *, code: str = "unsupported_media") -> None:
        super().__init__(detail, code=code, status_code=415, title="Định dạng không hỗ trợ")


class DependencyUnavailable(AppException):
    def __init__(self, detail: str, *, code: str = "dependency_unavailable") -> None:
        super().__init__(detail, code=code, status_code=503, title="Dịch vụ phụ thuộc không sẵn sàng")
