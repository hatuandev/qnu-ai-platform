"""No shell interpolation; binary streams, bounded deadlines, sanitized errors."""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.exceptions import AppException


def process_options() -> dict:
    return (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if os.name == "nt"
        else {"start_new_session": True}
    )


async def run_command(
    arguments: list[str],
    *,
    env: dict | None = None,
    source: Path | None = None,
    destination: Path | None = None,
    timeout: int = 120,
) -> bytes:
    # File descriptors avoid buffering a database dump in RAM or PowerShell text encoding.
    stdin = await asyncio.to_thread((source or Path(os.devnull)).open, "rb")
    try:
        output = await asyncio.to_thread(
            (destination or Path(os.devnull)).open, "xb" if destination else "wb"
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *arguments,
                stdin=stdin,
                stdout=output if destination else asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
                **process_options(),
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout)
            except BaseException:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
                raise
        finally:
            await asyncio.to_thread(output.close)
    finally:
        await asyncio.to_thread(stdin.close)
    if proc.returncode:
        raise AppException(
            f"Công cụ {Path(arguments[0]).name} thất bại (exit {proc.returncode}); kiểm tra kết nối/quyền và phiên bản.",
            code="BACKUP_TOOL_FAILED",
        )
    return stdout or b""


def pg_command(tool: str) -> tuple[list[str], dict]:
    url = make_url(settings.DATABASE_URL)
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    for option in ("sslmode", "sslrootcert", "sslcert", "sslkey", "connect_timeout"):
        if option in url.query:
            env["PG" + option.upper()] = str(url.query[option])
    executable = shutil.which(tool)
    if executable:
        return [
            executable,
            "-h",
            url.host or "localhost",
            "-p",
            str(url.port or 5432),
            "-U",
            url.username or "",
            "-d",
            url.database or "",
        ], env
    if not shutil.which("docker") or not settings.BACKUP_PG_CONTAINER:
        raise AppException(
            "Cần pg_dump cùng phiên bản PostgreSQL, hoặc Docker với BACKUP_PG_CONTAINER.",
            code="BACKUP_TOOL_MISSING",
        )
    return [
        "docker",
        "exec",
        "-i",
        "-e",
        "PGPASSWORD",
        settings.BACKUP_PG_CONTAINER,
        tool,
        "-h",
        "127.0.0.1",
        "-p",
        "5432",
        "-U",
        url.username or "",
        "-d",
        url.database or "",
    ], env


async def dump_database(destination: Path, connection) -> dict:
    major = int(await connection.fetchval("SHOW server_version_num")) // 10000
    args, env = pg_command("pg_dump")
    version_args = args[:-8] if args[0] == "docker" else args[:1]
    # The docker prefix includes its tool; remove connection options only.
    version = (await run_command([*version_args, "--version"], env=env)).decode().strip()
    if args[0] == "docker":
        # localhost inside a container is NOT necessarily the DATABASE_URL target.
        # Refuse a dump from a different PostgreSQL cluster even if DB names match.
        expected = str(
            await connection.fetchval("SELECT system_identifier FROM pg_control_system()")
        )
        identity_command = [*args]
        identity_command[identity_command.index("pg_dump")] = "psql"
        actual = (
            (
                await run_command(
                    [
                        *identity_command,
                        "-At",
                        "-c",
                        "SELECT system_identifier FROM pg_control_system()",
                    ],
                    env=env,
                )
            )
            .decode()
            .strip()
        )
        if actual != expected:
            raise AppException(
                "Container PostgreSQL không phải máy chủ DATABASE_URL; cài pg_dump native hoặc sửa BACKUP_PG_CONTAINER.",
                code="BACKUP_SOURCE_MISMATCH",
            )
    import re

    match = re.search(r"(\d+)\.\d+", version)
    if not match or int(match[1]) != major:
        raise AppException(
            "pg_dump phải cùng major version với PostgreSQL để khôi phục thử an toàn.",
            code="BACKUP_VERSION_MISMATCH",
        )
    await run_command(
        [*args, "--format=custom", "--no-owner", "--no-acl"],
        env=env,
        destination=destination,
        timeout=settings.BACKUP_TIMEOUT_SECONDS,
    )
    return {"major": major, "tool": version}
