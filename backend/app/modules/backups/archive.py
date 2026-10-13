"""Encrypted tar archive with exact inventory and traversal/link/bomb rejection."""

import hashlib
import io
import json
import tarfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.modules.backups.catalogue import json_bytes, sha256_file
from app.modules.backups.encryption import EncryptedWriter, decrypt_stream
from app.modules.backups.errors import BackupIntegrityError


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or ":" in name
        or "\x00" in name
        or PureWindowsPath(name).is_reserved()
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in name.split("/"))
    ):
        raise BackupIntegrityError("Đường dẫn trong bản sao lưu không an toàn.")
    return path.as_posix()


def add_bytes(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(safe_name(name))
    info.size, info.mode = len(data), 0o600
    archive.addfile(info, io.BytesIO(data))


def write_archive(
    destination: Path, password: str, files: dict[str, Path], manifest: dict, secrets: dict
) -> None:
    inventory = {
        safe_name(name): {"size": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in files.items()
    }
    secret_bytes = json_bytes(secrets)
    inventory["secrets.json"] = {
        "size": len(secret_bytes),
        "sha256": hashlib.sha256(secret_bytes).hexdigest(),
    }
    manifest["inventory"] = inventory
    with destination.open("xb") as output:
        writer = EncryptedWriter(output, password)
        with tarfile.open(fileobj=writer, mode="w|gz") as archive:
            add_bytes(archive, "manifest.json", json_bytes(manifest))
            add_bytes(archive, "secrets.json", secret_bytes)
            for name, path in files.items():
                info = tarfile.TarInfo(safe_name(name))
                info.size, info.mode = inventory[name]["size"], 0o600
                with path.open("rb") as source:
                    archive.addfile(info, source)
        writer.finish()


def extract_verified(source: Path, destination: Path, password: str, max_bytes: int) -> dict:
    # Private scratch only. No extractall and no links; validate every exact manifest entry.
    packed = destination / "payload.tar.gz"
    with source.open("rb") as encrypted, packed.open("xb") as plain:
        decrypt_stream(encrypted, plain, password, max_plain_bytes=max_bytes)
    total = 0
    seen: set[str] = set()
    manifest = None
    with tarfile.open(packed, mode="r|gz") as archive:
        for entry in archive:
            name = safe_name(entry.name)
            if not entry.isfile() or name in seen or entry.size < 0:
                raise BackupIntegrityError(
                    "Bản sao lưu chứa liên kết/entry trùng hoặc không hợp lệ."
                )
            seen.add(name)
            total += entry.size
            if total > max_bytes:
                raise BackupIntegrityError("Không đủ hạn mức dung lượng để giải nén bản sao lưu.")
            stream = archive.extractfile(entry)
            if stream is None:
                raise BackupIntegrityError("Thiếu nội dung bản sao lưu.")
            if name == "manifest.json":
                if manifest is not None or entry.size > 16 * 1024 * 1024:
                    raise BackupIntegrityError("Manifest không hợp lệ.")
                manifest = json.loads(stream.read())
                if manifest.get("format") != "qnu-backup-v1":
                    raise BackupIntegrityError("Phiên bản manifest không hỗ trợ.")
                continue
            if manifest is None or name not in manifest.get("inventory", {}):
                raise BackupIntegrityError("Entry không nằm trong manifest.")
            expected = manifest["inventory"][name]
            if entry.size != expected["size"]:
                raise BackupIntegrityError("Kích thước entry không khớp manifest.")
            target = destination / name
            if not target.resolve().is_relative_to(destination.resolve()) or target.is_symlink():
                raise BackupIntegrityError("Đường dẫn giải nén không an toàn.")
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            digest = hashlib.sha256()
            with target.open("xb") as output:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
                    output.write(chunk)
            if digest.hexdigest() != expected["sha256"]:
                raise BackupIntegrityError("Checksum dữ liệu không khớp manifest.")
    packed.unlink()
    if manifest is None or seen != {"manifest.json", *manifest.get("inventory", {})}:
        raise BackupIntegrityError("Bản sao lưu thiếu dữ liệu trong manifest.")
    return manifest
