"""Portable MD/JSON/image exports of a completed, pinned extraction result."""

import asyncio
import hashlib
import io
import json
import re
import zipfile

from qnu.domains.ocr.execution import read_artifact_bytes
from qnu.domains.ocr.service import processing_service
from qnu.platform.errors import AppException, EntityNotFound

MAX_BUNDLE_BYTES = 64 * 1024 * 1024


def images_in(document: dict) -> list[dict]:
    return [b["image"] for p in document["pages"] for b in p["blocks"] if b.get("image")]


async def read_image(db, blob, run, asset_no):
    _, payload = await processing_service.read_document(db, blob, run)
    image = next((v for v in images_in(json.loads(payload)) if v["asset_no"] == asset_no), None)
    if image is None:
        raise EntityNotFound(
            "Không tìm thấy ảnh trong kết quả này.", code="extraction_image_not_found"
        )
    return image, await _image_bytes(db, blob, run, image)


async def _image_bytes(db, blob, run, image):
    record, data = await read_artifact_bytes(db, blob, run, "embedded_image", image["asset_no"])
    if record.sha256 != image["sha256"]:
        raise AppException(
            "Ảnh không khớp bằng chứng đã ghim.", code="artifact_integrity_failed", status_code=502
        )
    return data


def _zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
    return output.getvalue()


async def bundle(db, blob, run):
    _, document = await processing_service.read_document(db, blob, run)
    markdown = await processing_service.read_markdown(db, blob, run)
    files = [("document.json", document), ("document.md", markdown)]
    size = len(document) + len(markdown)
    if size > MAX_BUNDLE_BYTES:
        raise AppException(
            "Gói kết quả vượt 64 MB; hãy tải từng tệp.",
            code="extraction_bundle_too_large",
            status_code=413,
        )
    for image in images_in(json.loads(document)):
        if not re.fullmatch(r"images/[0-9]+\.[a-z]+", image["filename"]):
            raise AppException(
                "Đường dẫn ảnh không hợp lệ.", code="artifact_integrity_failed", status_code=502
            )
        data = await _image_bytes(db, blob, run, image)
        size += len(data)
        if size > MAX_BUNDLE_BYTES:
            raise AppException(
                "Gói kết quả vượt 64 MB; hãy tải từng tệp.",
                code="extraction_bundle_too_large",
                status_code=413,
            )
        files.append((image["filename"], data))
    payload = await asyncio.to_thread(_zip, files)
    return hashlib.sha256(payload).hexdigest(), payload
