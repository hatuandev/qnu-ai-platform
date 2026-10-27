"""Authenticated encrypted data bundles; no SQL, executable restore or ZIP extraction."""

import base64
import hashlib
import io
import json
import zipfile

from cryptography.fernet import Fernet, InvalidToken

from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.platform.errors import Conflict, PayloadTooLarge

MAX_BYTES = 512 * 1024 * 1024
MAX_FILES = 10000
VERSION = "qnu.infrastructure-recovery/v1"


def cipher(key: str) -> Fernet:
    if len(key) < 32:
        raise Conflict("Khóa recovery riêng cần ít nhất 32 ký tự.", code="recovery_key_required")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


def pack(snapshot: dict, objects: dict[str, bytes], key: str) -> bytes:
    if len(objects) > MAX_FILES or sum(map(len, objects.values())) > MAX_BYTES:
        raise PayloadTooLarge("Recovery bundle vượt giới hạn.", code="recovery_limit")
    entries = [
        {"key": name, "sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
        for name, value in sorted(objects.items())
    ]
    manifest = {"schema_version": VERSION, "snapshot": snapshot, "objects": entries}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json_bytes(manifest))
        written = set()
        for item in entries:
            if item["sha256"] not in written:
                archive.writestr("objects/" + item["sha256"], objects[item["key"]])
                written.add(item["sha256"])
    if buffer.tell() > MAX_BYTES:
        raise PayloadTooLarge("Recovery bundle vượt giới hạn.", code="recovery_limit")
    return cipher(key).encrypt(buffer.getvalue())


def unpack(payload: bytes, key: str) -> tuple[dict, dict[str, bytes]]:
    if len(payload) > MAX_BYTES * 2:
        raise PayloadTooLarge("Recovery bundle vượt giới hạn.", code="recovery_limit")
    try:
        plaintext = cipher(key).decrypt(payload)
        with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
            info = archive.infolist()
            names = [item.filename for item in info]
            if (
                len(info) > MAX_FILES + 1
                or len(set(names)) != len(names)
                or sum(item.file_size for item in info) > MAX_BYTES
            ):
                raise ValueError("bounds")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest["schema_version"] != VERSION:
                raise ValueError("version")
            objects = {}
            for item in manifest["objects"]:
                value = archive.read("objects/" + item["sha256"])
                if (
                    len(value) != item["size"]
                    or hashlib.sha256(value).hexdigest() != item["sha256"]
                    or item["key"] in objects
                ):
                    raise ValueError("integrity")
                objects[item["key"]] = value
            if set(names) != {
                "manifest.json",
                *["objects/" + item["sha256"] for item in manifest["objects"]],
            }:
                raise ValueError("extra entries")
            return manifest["snapshot"], objects
    except (InvalidToken, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        raise Conflict(
            "Recovery bundle sai khóa, hỏng hoặc không hợp lệ.", code="recovery_bundle_invalid"
        ) from exc
