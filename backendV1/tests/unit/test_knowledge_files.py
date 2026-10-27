"""Pure file-intake rules: naming, signature proof, storage keys, streaming limits."""

from __future__ import annotations

import io
import zipfile

import pytest

from qnu.domains.knowledge.artifacts.files import (
    build_storage_key,
    content_disposition,
    detect_stored_file,
    read_limited,
    sanitize_file_name,
)
from qnu.platform.errors import PayloadTooLarge, UnsupportedMedia

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _docx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


def test_sanitize_strips_directories_and_control_characters() -> None:
    assert sanitize_file_name("../../etc/passwd") == "passwd"
    assert sanitize_file_name("C:\\tmp\\Quy chế.docx") == "Quy chế.docx"
    assert sanitize_file_name("  báo\u0000cáo\n.pdf  ") == "báocáo.pdf"


def test_sanitize_rejects_empty_and_dot_names() -> None:
    for value in ("", "   ", ".", "..", "...", "/"):
        with pytest.raises(UnsupportedMedia) as excinfo:
            sanitize_file_name(value)
        assert excinfo.value.code == "file_name_invalid"


def test_sanitize_truncates_but_keeps_extension() -> None:
    name = sanitize_file_name("a" * 400 + ".pdf")
    assert len(name) == 200
    assert name.endswith(".pdf")


def test_pdf_signature_is_proven_from_bytes() -> None:
    stored = detect_stored_file("Đề án.pdf", PDF_BYTES, 10_000)
    assert stored.content_type == "application/pdf"
    assert stored.size_bytes == len(PDF_BYTES)
    assert len(stored.sha256) == 64


def test_pdf_extension_with_other_bytes_is_rejected() -> None:
    with pytest.raises(UnsupportedMedia) as excinfo:
        detect_stored_file("fake.pdf", b"not a pdf at all", 10_000)
    assert excinfo.value.code == "file_signature_mismatch"


def test_docx_requires_word_part_inside_the_zip() -> None:
    stored = detect_stored_file("van-ban.docx", _docx_bytes(), 10_000)
    assert stored.content_type.endswith("wordprocessingml.document")
    with pytest.raises(UnsupportedMedia):
        detect_stored_file("van-ban.docx", b"PK\x03\x04broken", 10_000)


def test_text_formats_must_be_utf8_and_free_of_nul_bytes() -> None:
    assert detect_stored_file("ghi-chu.md", "# Tiêu đề\n".encode(), 10_000).extension == ".md"
    with pytest.raises(UnsupportedMedia) as excinfo:
        detect_stored_file("ghi-chu.txt", b"abc\x00def", 10_000)
    assert excinfo.value.code == "file_signature_mismatch"
    with pytest.raises(UnsupportedMedia):
        detect_stored_file("ghi-chu.txt", b"abc\xff\xfe", 10_000)


def test_unsupported_extension_is_rejected_before_reading_bytes() -> None:
    with pytest.raises(UnsupportedMedia) as excinfo:
        detect_stored_file("script.exe", b"MZ\x90\x00", 10_000)
    assert excinfo.value.code == "unsupported_file_type"


def test_empty_and_oversized_payloads_are_rejected() -> None:
    with pytest.raises(UnsupportedMedia) as empty:
        detect_stored_file("trong.pdf", b"", 10_000)
    assert empty.value.code == "file_empty"
    with pytest.raises(PayloadTooLarge):
        detect_stored_file("lon.pdf", PDF_BYTES, len(PDF_BYTES) - 1)


def test_storage_key_is_content_addressed_and_rejects_unsafe_ids() -> None:
    sha = "a" * 64
    key = build_storage_key("ws_1", "col_1", sha)
    assert key == f"v1/workspaces/ws_1/collections/col_1/blobs/aa/{sha}"
    assert build_storage_key("ws_1", "col_1", sha) == key
    for bad in ("../ws", "ws/1", "", "ws 1"):
        with pytest.raises(ValueError):
            build_storage_key(bad, "col_1", sha)
    with pytest.raises(ValueError):
        build_storage_key("ws_1", "col_1", "A" * 64)


def test_content_disposition_encodes_non_ascii_names() -> None:
    header = content_disposition("Quy chế đào tạo.pdf")
    assert header.startswith("attachment; filename*=UTF-8''")
    encoded = header.split("''", 1)[1]
    assert " " not in encoded
    assert "%20" in encoded


class _ChunkReader:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    async def read(self, size: int = -1) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


async def test_read_limited_stops_at_the_ceiling() -> None:
    payload = await read_limited(_ChunkReader([b"abc", b"de"]), 10)
    assert payload == b"abcde"
    with pytest.raises(PayloadTooLarge):
        await read_limited(_ChunkReader([b"abc", b"def"]), 5)
