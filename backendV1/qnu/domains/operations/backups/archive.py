"""Portable evidence archives: bounded ZIP entries addressed by hash, no executable restore."""

import hashlib
import io
import json
import zipfile

from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.platform.errors import Conflict, PayloadTooLarge

MAX_BYTES = 256 * 1024 * 1024
MAX_FILES = 10000


def pack(snapshot: dict, objects: list[tuple[str, bytes, str | None]]) -> tuple[bytes, dict]:
    stream = io.BytesIO()
    inventory = []
    total = 0
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key, payload, expected in objects:
            total += len(payload)
            if total > MAX_BYTES or len(inventory) >= MAX_FILES:
                raise PayloadTooLarge(
                    "Bản sao lưu vượt giới hạn dung lượng.", code="backup_limit_exceeded"
                )
            sha = hashlib.sha256(payload).hexdigest()
            if expected and expected != sha:
                raise Conflict(
                    "Tệp nguồn không khớp hash đã lưu.", code="backup_source_integrity_failed"
                )
            entry = "objects/" + hashlib.sha256(key.encode()).hexdigest()
            archive.writestr(entry, payload)
            inventory.append(
                {
                    "key": key,
                    "entry": entry,
                    "sha256": sha,
                    "size_bytes": len(payload),
                    "expected_sha256": expected,
                }
            )
        metadata = json_bytes(snapshot)
        if len(metadata) + total > MAX_BYTES:
            raise PayloadTooLarge("Snapshot vượt giới hạn sao lưu.", code="backup_limit_exceeded")
        archive.writestr("snapshot.json", metadata)
        manifest = {
            "schema_version": "qnu.evidence-backup/v1",
            "workspace_id": snapshot["workspace_id"],
            "snapshot_sha256": hashlib.sha256(metadata).hexdigest(),
            "objects": inventory,
            "credentials_included": False,
            "database_restore_supported": False,
            "snapshot_tables": {k: len(v) for k, v in snapshot["tables"].items()},
        }
        archive.writestr("manifest.json", json_bytes(manifest))
    return stream.getvalue(), manifest


def verify(payload: bytes, expected_sha: str | None = None) -> dict:
    if len(payload) > MAX_BYTES or (
        expected_sha and hashlib.sha256(payload).hexdigest() != expected_sha
    ):
        raise Conflict("Bản sao lưu không khớp hash/dung lượng.", code="backup_integrity_failed")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            names = [e.filename for e in entries]
            if (
                len(entries) > MAX_FILES + 2
                or len(set(names)) != len(names)
                or sum(e.file_size for e in entries) > MAX_BYTES
            ):
                raise ValueError("archive limits")
            manifest = json.loads(archive.read("manifest.json"))
            expected = {"manifest.json", "snapshot.json"} | {
                r["entry"] for r in manifest["objects"]
            }
            if set(names) != expected or manifest["schema_version"] != "qnu.evidence-backup/v1":
                raise ValueError("inventory mismatch")
            snapshot_raw = archive.read("snapshot.json")
            if hashlib.sha256(snapshot_raw).hexdigest() != manifest["snapshot_sha256"]:
                raise ValueError("snapshot mismatch")
            snapshot = json.loads(snapshot_raw)
            if (
                snapshot["workspace_id"] != manifest["workspace_id"]
                or manifest["snapshot_tables"] != {k: len(v) for k, v in snapshot["tables"].items()}
                or manifest["credentials_included"] is not False
                or manifest["database_restore_supported"] is not False
            ):
                raise ValueError("scope mismatch")
            keys = set()
            for item in manifest["objects"]:
                if (
                    item["key"] in keys
                    or item["entry"]
                    != "objects/" + hashlib.sha256(item["key"].encode()).hexdigest()
                ):
                    raise ValueError("unsafe inventory")
                keys.add(item["key"])
                data = archive.read(item["entry"])
                if (
                    len(data) != item["size_bytes"]
                    or hashlib.sha256(data).hexdigest() != item["sha256"]
                    or item["expected_sha256"] not in {None, item["sha256"]}
                ):
                    raise ValueError("object mismatch")
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        zipfile.BadZipFile,
        RuntimeError,
    ) as exc:
        raise Conflict(
            "Nội dung bản sao lưu hỏng hoặc không an toàn.", code="backup_integrity_failed"
        ) from exc
    return {
        "verified": True,
        "workspace_id": manifest["workspace_id"],
        "objects": len(manifest["objects"]),
        "snapshot_sha256": manifest["snapshot_sha256"],
        "snapshot_tables": manifest["snapshot_tables"],
        "database_restore_supported": False,
    }
