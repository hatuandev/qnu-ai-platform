"""System-level PostgreSQL + Qdrant backup export and verified upload-restore."""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Literal

import asyncpg
import httpx

from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict, DependencyUnavailable, PayloadTooLarge
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

MAX_UPLOAD_BYTES = 512 * 1024 * 1024
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 2000

_SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BackupTarget = Literal["all", "postgres", "qdrant"]


def _quote_ident(name: str) -> str:
    if not _SAFE_IDENT_RE.match(name):
        raise Conflict(f"Tên bảng không hợp lệ trong bản sao lưu: {name!r}", code="backup_integrity_failed")
    return f'"{name}"'


def _qdrant_headers(api_key: str | None) -> dict[str, str]:
    key = (api_key or "").strip()
    return {"api-key": key} if key else {}


def _compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _safe_extract_tar_gz(archive_path: Path, dest_dir: Path) -> list[str]:
    """Safely extract a .tar.gz archive enforcing path traversal, symlink, and size bounds."""
    extracted: list[str] = []
    total_size = 0
    dest_resolved = dest_dir.resolve()
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getmembers()
            if not members:
                raise ValueError("Archive rỗng.")
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ValueError("Số lượng tệp trong bản sao lưu vượt giới hạn cho phép.")
            for member in members:
                if member.issym() or member.islnk() or member.isdev():
                    raise ValueError(f"Tệp không an toàn trong bản sao lưu: {member.name}")
                norm_name = member.name.replace("\\", "/").lstrip("/")
                if not norm_name or ".." in norm_name.split("/"):
                    raise ValueError(f"Đường dẫn không hợp lệ trong bản sao lưu: {member.name}")
                target = (dest_dir / norm_name).resolve()
                if dest_resolved not in target.parents and target != dest_resolved:
                    raise ValueError(f"Đường dẫn vượt phạm vi giải nén: {member.name}")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                total_size += member.size
                if total_size > MAX_EXPANDED_BYTES:
                    raise PayloadTooLarge(
                        "Dung lượng giải nén vượt giới hạn cho phép.",
                        code="backup_limit_exceeded",
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                src = tar.extractfile(member)
                if src is None:
                    continue
                with src, target.open("wb") as out:
                    shutil.copyfileobj(src, out, length=65536)
                extracted.append(norm_name)
    except AppException:
        raise
    except (tarfile.TarError, OSError, ValueError) as exc:
        raise Conflict(
            f"Tệp sao lưu không hợp lệ hoặc bị hỏng: {exc}",
            code="backup_integrity_failed",
        ) from exc
    return extracted


async def _export_postgres_native(db_dsn: str, out_file: Path) -> dict[str, Any]:
    raw_dsn = db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(raw_dsn)
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            alembic_head = None
            try:
                alembic_head = await conn.fetchval(
                    "SELECT version_num FROM alembic_version_backendv1 LIMIT 1"
                )
            except Exception:
                pass
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            table_names = [row["table_name"] for row in tables]
            table_stats: dict[str, int] = {}
            total_rows = 0
            now_dt = datetime.datetime.now(datetime.UTC)
            columns_meta: dict[str, list[dict[str, Any]]] = {}

            with tarfile.open(out_file, "w:gz") as tar:
                for tbl in table_names:
                    cols = await conn.fetch(
                        """
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = $1
                        ORDER BY ordinal_position
                        """,
                        tbl,
                    )
                    columns_meta[tbl] = [
                        {
                            "name": c["column_name"],
                            "type": c["data_type"],
                            "nullable": c["is_nullable"] == "YES",
                        }
                        for c in cols
                    ]
                    buf = io.BytesIO()
                    await conn.copy_from_table(tbl, output=buf, format="csv", header=True)
                    csv_bytes = buf.getvalue()
                    buf.close()

                    row_count = int(await conn.fetchval(f"SELECT count(*) FROM {_quote_ident(tbl)}") or 0)
                    table_stats[tbl] = row_count
                    total_rows += row_count

                    info = tarfile.TarInfo(name=f"tables/{tbl}.csv")
                    info.size = len(csv_bytes)
                    info.mtime = int(now_dt.timestamp())
                    tar.addfile(info, io.BytesIO(csv_bytes))

                meta_bytes = json.dumps(
                    {
                        "schema_version": "qnu.postgres-dump/v1",
                        "alembic_head": alembic_head,
                        "table_count": len(table_names),
                        "total_rows": total_rows,
                        "table_stats": table_stats,
                        "columns": columns_meta,
                    },
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8")
                meta_info = tarfile.TarInfo(name="schema_metadata.json")
                meta_info.size = len(meta_bytes)
                meta_info.mtime = int(now_dt.timestamp())
                tar.addfile(meta_info, io.BytesIO(meta_bytes))

        return {
            "tool": "asyncpg_native",
            "format": "tar_gz",
            "alembic_head": alembic_head,
            "table_count": len(table_names),
            "total_rows": total_rows,
            "table_stats": table_stats,
            "size_bytes": out_file.stat().st_size,
            "sha256": _compute_file_sha256(out_file),
        }
    finally:
        await conn.close()


async def _export_qdrant_snapshots(
    qdrant_url: str, out_dir: Path, api_key: str | None
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    headers = _qdrant_headers(api_key)
    async with httpx.AsyncClient(timeout=120.0, headers=headers) as client:
        resp = await client.get(f"{qdrant_url.rstrip('/')}/collections")
        if resp.status_code != 200:
            raise DependencyUnavailable(
                f"Không kết nối được Qdrant ({resp.status_code}).",
                code="qdrant_backup_unavailable",
            )
        collections = [
            c["name"] for c in resp.json().get("result", {}).get("collections", [])
        ]
        for col in collections:
            snap_resp = await client.post(f"{qdrant_url.rstrip('/')}/collections/{col}/snapshots")
            if snap_resp.status_code != 200:
                raise DependencyUnavailable(
                    f"Không tạo được snapshot Qdrant cho '{col}' ({snap_resp.status_code}).",
                    code="qdrant_backup_failed",
                )
            snap_name = snap_resp.json().get("result", {}).get("name")
            if not snap_name:
                raise DependencyUnavailable(
                    f"Qdrant không trả về tên snapshot cho '{col}'.",
                    code="qdrant_backup_failed",
                )
            target_file = out_dir / f"{col}.snapshot"
            try:
                async with client.stream(
                    "GET", f"{qdrant_url.rstrip('/')}/collections/{col}/snapshots/{snap_name}"
                ) as stream_resp:
                    if stream_resp.status_code != 200:
                        raise DependencyUnavailable(
                            f"Không tải được snapshot Qdrant '{snap_name}'.",
                            code="qdrant_backup_failed",
                        )
                    with target_file.open("wb") as out:
                        async for chunk in stream_resp.aiter_bytes(chunk_size=65536):
                            out.write(chunk)
            finally:
                try:
                    await client.delete(
                        f"{qdrant_url.rstrip('/')}/collections/{col}/snapshots/{snap_name}"
                    )
                except Exception:
                    logger.warning("qdrant_temp_snapshot_cleanup_failed", collection=col)

            results.append(
                {
                    "collection": col,
                    "path": f"qdrant/{col}.snapshot",
                    "size_bytes": target_file.stat().st_size,
                    "sha256": _compute_file_sha256(target_file),
                }
            )
    return results


def _pack_directory_tar_gz(source_dir: Path, bundle_path: Path) -> bytes:
    with tarfile.open(bundle_path, "w:gz") as tar:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(source_dir).as_posix())
    return bundle_path.read_bytes()


async def export_system_backup(target: BackupTarget = "all") -> tuple[bytes, str, dict[str, Any]]:
    """Create a verified, single-file .tar.gz system backup bundle for immediate download."""
    settings = get_settings()
    now_utc = datetime.datetime.now(datetime.UTC)
    timestamp = now_utc.strftime("%Y%m%d_%H%M%S")
    backup_id = f"backup_{timestamp}"
    filename = f"qnu-system-backup-{timestamp}.tar.gz"

    with tempfile.TemporaryDirectory(prefix="qnu_sys_backup_") as tmp:
        root = Path(tmp) / "content"
        root.mkdir(parents=True, exist_ok=True)
        items: list[dict[str, Any]] = []
        alembic_head = None

        if target in {"all", "postgres"}:
            pg_dir = root / "postgres"
            pg_dir.mkdir(parents=True, exist_ok=True)
            pg_file = pg_dir / "database_dump.tar.gz"
            pg_info = await _export_postgres_native(settings.DATABASE_URL, pg_file)
            alembic_head = pg_info.get("alembic_head")
            items.append(
                {
                    "kind": "postgres",
                    "path": "postgres/database_dump.tar.gz",
                    "tool": pg_info["tool"],
                    "format": pg_info["format"],
                    "size_bytes": pg_info["size_bytes"],
                    "sha256": pg_info["sha256"],
                    "table_count": pg_info["table_count"],
                    "total_rows": pg_info["total_rows"],
                }
            )

        if target in {"all", "qdrant"}:
            qdrant_items = await _export_qdrant_snapshots(
                settings.QDRANT_URL, root / "qdrant", settings.QDRANT_API_KEY
            )
            for item in qdrant_items:
                items.append({"kind": "qdrant", **item})

        manifest = {
            "schema_version": "qnu.system-backup/v1",
            "backup_id": backup_id,
            "created_at": now_utc.isoformat(),
            "target": target,
            "alembic_head": alembic_head,
            "platform_version": "v1",
            "items": items,
            "status": "completed",
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        bundle_path = Path(tmp) / filename
        bundle_bytes = await asyncio.to_thread(_pack_directory_tar_gz, root, bundle_path)
        bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
        return bundle_bytes, filename, {**manifest, "bundle_sha256": bundle_sha, "bundle_size_bytes": len(bundle_bytes)}


async def _restore_postgres_native_archive(db_dsn: str, archive_path: Path) -> dict[str, Any]:
    """Atomically truncate all target tables once, then COPY and re-sync sequences."""
    raw_dsn = db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(raw_dsn)
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            meta_member = tar.getmember("schema_metadata.json")
            meta_file = tar.extractfile(meta_member)
            if not meta_file:
                raise Conflict("Thiếu schema_metadata.json trong bản sao lưu.", code="backup_integrity_failed")
            meta = json.loads(meta_file.read().decode("utf-8"))
            tables_raw = meta.get("tables") or meta.get("columns") or {}
            if not tables_raw:
                tables_raw = {t: [] for t in meta.get("table_stats", {})}
            table_payloads: list[tuple[str, bytes]] = []
            for tbl in tables_raw:
                _quote_ident(tbl)
                csv_name = f"tables/{tbl}.csv"
                try:
                    member = tar.getmember(csv_name)
                except KeyError:
                    continue
                handle = tar.extractfile(member)
                if handle is None:
                    continue
                table_payloads.append((tbl, handle.read()))

        replica_mode = False
        try:
            await conn.execute("SET session_replication_role = 'replica'")
            replica_mode = True
        except Exception:
            pass

        restored_stats: dict[str, int] = {}
        try:
            async with conn.transaction():
                if table_payloads:
                    quoted_all = ", ".join(_quote_ident(tbl) for tbl, _ in table_payloads)
                    await conn.execute(
                        f"TRUNCATE TABLE {quoted_all} RESTART IDENTITY CASCADE"
                    )
                for tbl, csv_bytes in table_payloads:
                    if csv_bytes.strip():
                        await conn.copy_to_table(
                            tbl, source=io.BytesIO(csv_bytes), format="csv", header=True
                        )
                for tbl, _ in table_payloads:
                    cnt = await conn.fetchval(f"SELECT count(*) FROM {_quote_ident(tbl)}")
                    restored_stats[tbl] = int(cnt or 0)

                seq_query = """
                    SELECT sequence_name, table_name, column_name
                    FROM information_schema.sequences s
                    JOIN information_schema.columns c
                      ON c.column_default LIKE '%' || s.sequence_name || '%'
                    WHERE sequence_schema = 'public'
                """
                try:
                    seqs = await conn.fetch(seq_query)
                    for sq in seqs:
                        max_val = await conn.fetchval(
                            f"SELECT MAX({_quote_ident(sq['column_name'])}) FROM {_quote_ident(sq['table_name'])}"
                        )
                        if max_val is None:
                            await conn.execute(
                                "SELECT setval($1::regclass, 1, false)", sq["sequence_name"]
                            )
                        else:
                            await conn.execute(
                                "SELECT setval($1::regclass, $2, true)",
                                sq["sequence_name"],
                                int(max_val),
                            )
                except Exception:
                    pass
        finally:
            if replica_mode:
                try:
                    await conn.execute("SET session_replication_role = 'origin'")
                except Exception:
                    pass

        return {
            "status": "restored",
            "tool": "asyncpg_native",
            "table_count": len(restored_stats),
            "total_rows_restored": sum(restored_stats.values()),
        }
    finally:
        await conn.close()


def _restore_postgres_pg_dump(db_dsn: str, dump_path: Path) -> dict[str, Any]:
    if shutil.which("pg_restore") is None:
        raise DependencyUnavailable(
            "Máy chủ chưa cài đặt công cụ pg_restore để phục hồi định dạng .dump.",
            code="pg_restore_unavailable",
        )
    with dump_path.open("rb") as f:
        if f.read(5) != b"PGDMP":
            raise Conflict("Tệp .dump không đúng định dạng PostgreSQL custom.", code="backup_integrity_failed")
    raw_dsn = db_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urllib.parse.urlparse(raw_dsn)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--single-transaction",
        "-h", parsed.hostname or "127.0.0.1",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/") or "postgres",
        str(dump_path),
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise Conflict(f"pg_restore thất bại: {result.stderr.strip()[:400]}", code="backup_restore_failed")
    return {
        "status": "restored",
        "tool": "pg_dump_custom",
        "size_bytes": dump_path.stat().st_size,
    }


async def _restore_qdrant_snapshots(
    qdrant_url: str, root_dir: Path, items: list[dict[str, Any]], api_key: str | None
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    headers = _qdrant_headers(api_key)
    base = qdrant_url.rstrip("/")
    async with httpx.AsyncClient(timeout=300.0, headers=headers) as client:
        for item in items:
            col = item["collection"]
            snap_file = root_dir / item["path"]
            if not snap_file.is_file():
                raise Conflict(
                    f"Thiếu tệp snapshot Qdrant cho '{col}'.",
                    code="backup_integrity_failed",
                )
            with snap_file.open("rb") as handle:
                resp = await client.post(
                    f"{base}/collections/{col}/snapshots/upload",
                    files={"snapshot": (snap_file.name, handle, "application/octet-stream")},
                )
            if resp.status_code not in {200, 201}:
                raise DependencyUnavailable(
                    f"Khôi phục Qdrant '{col}' thất bại ({resp.status_code}).",
                    code="qdrant_restore_failed",
                )
            points_count = None
            info_resp = await client.get(f"{base}/collections/{col}")
            if info_resp.status_code == 200:
                points_count = info_resp.json().get("result", {}).get("points_count")
            results.append({"collection": col, "status": "restored", "points_count": points_count})
    return results


async def inspect_and_restore_system_backup(
    payload: bytes,
    filename: str,
    *,
    target: BackupTarget = "all",
    confirm: bool = False,
) -> dict[str, Any]:
    """Verify an uploaded backup archive and optionally restore PostgreSQL and/or Qdrant."""
    if not payload:
        raise Conflict("Tệp sao lưu rỗng.", code="backup_integrity_failed")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise PayloadTooLarge("Tệp sao lưu vượt giới hạn dung lượng (512 MB).", code="backup_limit_exceeded")

    upload_sha = hashlib.sha256(payload).hexdigest()
    settings = get_settings()

    with tempfile.TemporaryDirectory(prefix="qnu_sys_restore_") as tmp:
        tmp_path = Path(tmp)
        safe_name = Path(filename or "backup.tar.gz").name
        uploaded_file = tmp_path / safe_name
        uploaded_file.write_bytes(payload)

        # Case 1: PostgreSQL custom dump (.dump / PGDMP header)
        if payload[:5] == b"PGDMP":
            summary: dict[str, Any] = {
                "status": "verified",
                "format": "pg_dump_custom",
                "backup_id": safe_name,
                "created_at": None,
                "alembic_head": None,
                "postgres_tables": None,
                "postgres_rows": None,
                "qdrant_collections": [],
                "total_bytes": len(payload),
                "sha256": upload_sha,
                "targets": {},
            }
            if not confirm:
                return summary
            if target == "qdrant":
                raise Conflict(
                    "Tệp .dump chỉ chứa dữ liệu PostgreSQL, không chứa Qdrant.",
                    code="backup_target_unavailable",
                )
            pg_res = await asyncio.to_thread(_restore_postgres_pg_dump, settings.DATABASE_URL, uploaded_file)
            return {**summary, "status": "restored", "targets": {"postgres": pg_res}}

        # Case 2 & 3: .tar.gz archive (either full system bundle or native postgres archive)
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        members = await asyncio.to_thread(_safe_extract_tar_gz, uploaded_file, extract_dir)

        manifest_path = extract_dir / "manifest.json"
        schema_meta_path = extract_dir / "schema_metadata.json"

        # Case 2: Standalone native postgres archive (database_dump.tar.gz)
        if not manifest_path.is_file() and schema_meta_path.is_file():
            meta = json.loads(schema_meta_path.read_text(encoding="utf-8"))
            summary = {
                "status": "verified",
                "format": "postgres_native_tar_gz",
                "backup_id": safe_name,
                "created_at": None,
                "alembic_head": meta.get("alembic_head"),
                "postgres_tables": meta.get("table_count") or len(meta.get("table_stats") or {}),
                "postgres_rows": meta.get("total_rows"),
                "qdrant_collections": [],
                "total_bytes": len(payload),
                "sha256": upload_sha,
                "targets": {},
            }
            if not confirm:
                return summary
            if target == "qdrant":
                raise Conflict(
                    "Tệp sao lưu này chỉ chứa PostgreSQL, không chứa Qdrant.",
                    code="backup_target_unavailable",
                )
            pg_res = await _restore_postgres_native_archive(settings.DATABASE_URL, uploaded_file)
            return {**summary, "status": "restored", "targets": {"postgres": pg_res}}

        # Case 3: Full system backup bundle with manifest.json
        if not manifest_path.is_file():
            raise Conflict(
                "Tệp sao lưu không chứa manifest.json hoặc schema_metadata.json hợp lệ.",
                code="backup_integrity_failed",
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != "qnu.system-backup/v1":
            raise Conflict(
                f"Phiên bản manifest không được hỗ trợ: {manifest.get('schema_version')}",
                code="backup_integrity_failed",
            )

        pg_item: dict[str, Any] | None = None
        qdrant_items: list[dict[str, Any]] = []
        for item in manifest.get("items", []):
            rel = str(item.get("path") or "").replace("\\", "/")
            if not rel or ".." in rel.split("/") or rel.startswith("/"):
                raise Conflict("Đường dẫn tệp không hợp lệ trong manifest.", code="backup_integrity_failed")
            artifact = (extract_dir / rel).resolve()
            if extract_dir.resolve() not in artifact.parents or not artifact.is_file():
                raise Conflict(f"Thiếu thành phần sao lưu: {rel}", code="backup_integrity_failed")
            if artifact.stat().st_size != item.get("size_bytes"):
                raise Conflict(f"Sai kích thước tệp sao lưu: {rel}", code="backup_integrity_failed")
            if _compute_file_sha256(artifact) != item.get("sha256"):
                raise Conflict(f"Sai mã băm SHA-256 cho tệp: {rel}", code="backup_integrity_failed")
            if item.get("kind") == "postgres":
                if artifact.name.endswith(".dump") or item.get("tool") == "pg_dump_custom":
                    with artifact.open("rb") as f:
                        if f.read(5) != b"PGDMP":
                            raise Conflict("Tệp PostgreSQL .dump bị hỏng.", code="backup_integrity_failed")
                else:
                    with tarfile.open(artifact, "r:gz") as sub_tar:
                        if "schema_metadata.json" not in sub_tar.getnames():
                            raise Conflict(
                                "Tệp PostgreSQL .tar.gz thiếu schema_metadata.json.",
                                code="backup_integrity_failed",
                            )
                pg_item = item
            elif item.get("kind") == "qdrant":
                qdrant_items.append(item)

        summary = {
            "status": "verified",
            "format": "system_bundle_tar_gz",
            "backup_id": manifest.get("backup_id") or safe_name,
            "created_at": manifest.get("created_at"),
            "alembic_head": manifest.get("alembic_head"),
            "postgres_tables": pg_item.get("table_count") if pg_item else 0,
            "postgres_rows": pg_item.get("total_rows") if pg_item else 0,
            "qdrant_collections": [item["collection"] for item in qdrant_items],
            "total_bytes": len(payload),
            "sha256": upload_sha,
            "members_count": len(members),
            "targets": {},
        }
        if not confirm:
            return summary

        # Pre-flight Qdrant connectivity check before mutating PostgreSQL
        if target == "all" and qdrant_items:
            async with httpx.AsyncClient(
                timeout=15.0, headers=_qdrant_headers(settings.QDRANT_API_KEY)
            ) as client:
                health = await client.get(f"{settings.QDRANT_URL.rstrip('/')}/collections")
                if health.status_code != 200:
                    raise DependencyUnavailable(
                        f"Qdrant không sẵn sàng ({health.status_code}); đã hủy trước khi ghi đè PostgreSQL để giữ nhất quán.",
                        code="qdrant_restore_preflight_failed",
                    )

        restored_targets: dict[str, Any] = {}
        pg_restored = False
        if target in {"all", "postgres"} and pg_item is not None:
            pg_artifact = extract_dir / pg_item["path"]
            is_pg_dump = (
                pg_item.get("tool") == "pg_dump_custom"
                or pg_item.get("format") == "pg_dump_custom"
                or pg_artifact.name.endswith(".dump")
            )
            if is_pg_dump:
                restored_targets["postgres"] = await asyncio.to_thread(
                    _restore_postgres_pg_dump, settings.DATABASE_URL, pg_artifact
                )
            else:
                restored_targets["postgres"] = await _restore_postgres_native_archive(
                    settings.DATABASE_URL, pg_artifact
                )
            pg_restored = True

        if target in {"all", "qdrant"} and qdrant_items:
            try:
                restored_targets["qdrant"] = await _restore_qdrant_snapshots(
                    settings.QDRANT_URL, extract_dir, qdrant_items, settings.QDRANT_API_KEY
                )
            except Exception as exc:
                if pg_restored:
                    raise DependencyUnavailable(
                        "PostgreSQL đã khôi phục nhưng Qdrant gặp sự cố. Hãy chạy lại khôi phục với phạm vi chỉ Qdrant để đồng bộ.",
                        code="qdrant_restore_partial_failure",
                    ) from exc
                raise

        return {**summary, "status": "restored", "targets": restored_targets}
