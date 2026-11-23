"""File intake rules for knowledge sources: naming, format proof, checksum and blob keys.

Nothing here parses document content. A file that passes these checks is *stored*,
not *parsed*, and the API must keep saying so.
"""

from __future__ import annotations

import codecs
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import quote

from qnu.platform.errors import PayloadTooLarge, UnsupportedMedia

SUPPORTED_FORMATS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}

TEXT_FORMATS = frozenset({".txt", ".md"})
ZIP_FORMATS = {".docx": "word/", ".xlsx": "xl/", ".pptx": "ppt/"}

MAX_FILE_NAME_LENGTH = 200
READ_CHUNK_BYTES = 1024 * 1024
TEXT_PROBE_BYTES = 64 * 1024

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ILLEGAL_NAME_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class AsyncByteReader(Protocol):
    """Minimal reader surface shared by ``UploadFile`` and test doubles."""

    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True, slots=True)
class StoredFile:
    """Result of intake validation, computed from the real bytes."""

    file_name: str
    extension: str
    content_type: str
    size_bytes: int
    sha256: str


def sanitize_file_name(raw: str) -> str:
    """Keep a display name only: no directories, control characters or dot names."""
    candidate = (raw or "").replace("\\", "/")
    candidate = PurePosixPath(candidate).name
    candidate = _ILLEGAL_NAME_CHARS.sub("", candidate)
    candidate = " ".join(candidate.split()).strip().strip(".")
    if not candidate or candidate in {".", ".."}:
        raise UnsupportedMedia("Tên tệp không hợp lệ.", code="file_name_invalid")
    if len(candidate) > MAX_FILE_NAME_LENGTH:
        suffix = PurePosixPath(candidate).suffix
        keep = MAX_FILE_NAME_LENGTH - len(suffix)
        candidate = candidate[:keep] + suffix
    return candidate


def file_extension(file_name: str) -> str:
    return PurePosixPath(file_name).suffix.lower()


def _prove_pdf(payload: bytes) -> bool:
    return payload.startswith(b"%PDF-")


def _prove_zip(payload: bytes, extension: str) -> bool:
    if not payload.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False
    if extension == ".pptx":
        return "[Content_Types].xml" in names and "ppt/presentation.xml" in names
    prefix = ZIP_FORMATS[extension]
    return any(name.startswith(prefix) for name in names)


def _prove_text(payload: bytes) -> bool:
    head = payload[:TEXT_PROBE_BYTES]
    if b"\x00" in head[:8192]:
        return False
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        decoder.decode(head, final=False)
    except UnicodeDecodeError:
        return False
    return True


def detect_stored_file(file_name: str, payload: bytes, max_bytes: int) -> StoredFile:
    """Validate size, extension and real signature; never trust the client content type."""
    if not payload:
        raise UnsupportedMedia("Tệp rỗng.", code="file_empty")
    if len(payload) > max_bytes:
        raise PayloadTooLarge(
            f"Tệp vượt giới hạn {max_bytes} byte.", code="payload_too_large"
        )

    safe_name = sanitize_file_name(file_name)
    extension = file_extension(safe_name)
    if extension not in SUPPORTED_FORMATS:
        allowed = ", ".join(sorted(SUPPORTED_FORMATS))
        raise UnsupportedMedia(
            f"Định dạng '{extension or 'không rõ'}' không được hỗ trợ ({allowed}).",
            code="unsupported_file_type",
        )

    if extension == ".pdf":
        matched = _prove_pdf(payload)
    elif extension in ZIP_FORMATS:
        matched = _prove_zip(payload, extension)
    else:
        matched = _prove_text(payload)
    if not matched:
        raise UnsupportedMedia(
            "Nội dung tệp không khớp phần mở rộng đã khai báo.", code="file_signature_mismatch"
        )

    return StoredFile(
        file_name=safe_name,
        extension=extension,
        content_type=SUPPORTED_FORMATS[extension],
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


async def read_limited(reader: AsyncByteReader, max_bytes: int) -> bytes:
    """Read a stream with a hard ceiling so an oversized upload is never buffered whole."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await reader.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLarge(
                f"Tệp vượt giới hạn {max_bytes} byte.", code="payload_too_large"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def build_storage_key(workspace_id: str, collection_id: str, sha256: str) -> str:
    """Content-addressed key: the client file name never decides which object is written."""
    for value in (workspace_id, collection_id):
        if not _SAFE_ID.fullmatch(value):
            raise ValueError("Unsafe identifier in storage key.")
    if not _SHA256.fullmatch(sha256):
        raise ValueError("sha256 must be 64 lowercase hex characters.")
    return f"v1/workspaces/{workspace_id}/collections/{collection_id}/blobs/{sha256[:2]}/{sha256}"


def content_disposition(file_name: str) -> str:
    """RFC 5987 attachment header; the raw name never reaches the header unencoded."""
    return f"attachment; filename*=UTF-8''{quote(file_name, safe='')}"
