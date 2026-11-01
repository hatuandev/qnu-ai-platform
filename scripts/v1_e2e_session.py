"""Persistent, explicitly owned E2E infrastructure. Import has no side effects."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tmp" / "v1-e2e"
BE, FE = ROOT / "backendV1", ROOT / "frontendV1"
PYTHON = BE / ".venv/Scripts/python.exe"
STAGES = (
    "navigation",
    "upload",
    "extraction",
    "compilation",
    "publication",
    "chat",
    "permissions",
    "lifecycle",
)
MODEL_STAGES = (
    "provider-setup",
    "model-discovery",
    "model-chat",
    "model-embedding",
    "model-rerank",
    "model-ocr",
)
ADMISSIONS_STAGES = (
    "admissions-upload",
    "admissions-extraction",
    "admissions-draft",
    "admissions-compilation",
    "admissions-publication",
    "admissions-chat",
)


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def backend_source_hash():
    digest = hashlib.sha256()
    for source in sorted((BE / "qnu").rglob("*.py")):
        digest.update(source.relative_to(BE).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(source.read_bytes()).digest())
    return digest.hexdigest()


def load_session(run_id=None):
    if run_id is None and not (BASE / "active.json").exists():
        raise RuntimeError("Chưa có phiên E2E. Chạy init trước.")
    run_id = run_id or read(BASE / "active.json")["run_id"]
    if not re.fullmatch(r"[a-f0-9]{12}", run_id):
        raise RuntimeError("RUN_ID không hợp lệ.")
    directory = BASE / run_id
    manifest = read(directory / "manifest.json")
    if manifest["run_id"] != run_id or manifest["project"] != "qnu-e2e-" + run_id:
        raise RuntimeError("Manifest không thuộc phiên thử.")
    if (
        hashlib.sha256((directory / "compose.json").read_bytes()).hexdigest()
        != manifest["compose_sha256"]
    ):
        raise RuntimeError("Compose đã đổi; từ chối thao tác hạ tầng.")
    return directory, manifest


def compose(directory, manifest, *args):
    subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            manifest["project"],
            "-f",
            str(directory / "compose.json"),
            *args,
        ],
        check=True,
    )


def ports():
    sockets, result = [], {}
    try:
        for name in (
            "postgres",
            "redis",
            "minio",
            "qdrant",
            "gotenberg",
            "api",
            "frontend",
            "mock",
        ):
            sock = socket.socket()
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
            result[name] = sock.getsockname()[1]
        return result
    finally:
        for sock in sockets:
            sock.close()


def initialize(mode):
    if (
        not PYTHON.is_file()
        or not shutil.which("node")
        or not (FE / "node_modules/@playwright/test/cli.js").is_file()
    ):
        raise RuntimeError(
            "Cần backendV1 .venv, Node và npm ci trong frontendV1 trước."
        )
    BASE.mkdir(parents=True, exist_ok=True)
    if (BASE / "active.json").exists() and not load_session()[1].get("cleaned"):
        raise RuntimeError("Còn phiên cũ; status/cleanup trước khi init phiên mới.")
    run_id, password, assigned = (
        secrets.token_hex(6),
        secrets.token_urlsafe(24),
        ports(),
    )
    directory = BASE / run_id
    directory.mkdir()
    env = {
        "ENVIRONMENT": "test",
        "API_PREFIX": "/platform/v1alpha1",
        "SSO_ENABLED": "false",
        "DEV_AUTH_ENABLED": "true",
        "DEV_ACCESS_PASSWORD": secrets.token_urlsafe(24),
        "SECRET_KEY": secrets.token_urlsafe(48),
        "PROVIDER_ENCRYPTION_KEY": secrets.token_urlsafe(48),
        "DATABASE_URL": f"postgresql+asyncpg://e2e:{password}@127.0.0.1:{assigned['postgres']}/qnu_v1_test_e2e_{run_id}",
        "REDIS_URL": f"redis://127.0.0.1:{assigned['redis']}/0",
        "QUEUE_NAME": f"qnu:e2e:{run_id}",
        "CACHE_NAMESPACE": f"qnu:e2e:{run_id}:",
        "STORAGE_DRIVER": "s3",
        "S3_ENDPOINT": f"http://127.0.0.1:{assigned['minio']}",
        "S3_BUCKET": f"qnu-e2e-{run_id}",
        "S3_ACCESS_KEY": "e2e_admin",
        "S3_SECRET_KEY": password,
        "S3_SECURE": "false",
        "QDRANT_URL": f"http://127.0.0.1:{assigned['qdrant']}",
        "GOTENBERG_URL": f"http://127.0.0.1:{assigned['gotenberg']}",
        "OWN_RECONCILE": "true",
        "OCR_RENDER_DPI": "144",
        "OCR_MAX_OUTPUT_TOKENS": "4096",
        "COMPILER_MAX_OUTPUT_TOKENS": "8192",
        "RAG_MAX_OUTPUT_TOKENS": "4096",
        "DOCX_CONVERTER": "gotenberg-libreoffice",
        "VECTOR_SIZE": "1024",
        "PORT": str(assigned["api"]),
        "HOST": "127.0.0.1",
        "PUBLIC_BASE_URL": f"http://127.0.0.1:{assigned['api']}",
        "ALLOWED_ORIGINS": f"http://127.0.0.1:{assigned['frontend']}",
        "PYTHONIOENCODING": "utf-8",
    }
    definitions = {
        "postgres": (
            "postgres:16",
            5432,
            {
                "POSTGRES_USER": "e2e",
                "POSTGRES_PASSWORD": password,
                "POSTGRES_DB": f"qnu_v1_test_e2e_{run_id}",
            },
            "/var/lib/postgresql/data",
        ),
        "redis": ("redis:7-alpine", 6379, {}, "/data"),
        "minio": (
            "pgsty/minio:RELEASE.2026-06-18T00-00-00Z",
            9000,
            {"MINIO_ROOT_USER": "e2e_admin", "MINIO_ROOT_PASSWORD": password},
            "/data",
        ),
        "qdrant": ("qdrant/qdrant:latest", 6333, {}, "/qdrant/storage"),
        "gotenberg": ("gotenberg/gotenberg:8", 3000, {}, None),
    }
    services, volumes = {}, {}
    for name, (image, port, environment, mount) in definitions.items():
        item = {
            "image": image,
            "ports": [f"127.0.0.1:{assigned[name]}:{port}"],
            "environment": environment,
            "labels": {"qnu.e2e.run": run_id},
        }
        if mount:
            item["volumes"] = [f"{name}_data:{mount}"]
            volumes[name + "_data"] = {}
        if name == "minio":
            item["command"] = ["server", "/data"]
        services[name] = item
    save(directory / "compose.json", {"services": services, "volumes": volumes})
    manifest = {
        "run_id": run_id,
        "project": "qnu-e2e-" + run_id,
        "ports": assigned,
        "mode": mode,
        "compose_sha256": hashlib.sha256(
            (directory / "compose.json").read_bytes()
        ).hexdigest(),
        "cleaned": False,
    }
    save(directory / "manifest.json", manifest)
    save(directory / "private-env.json", env)
    save(
        directory / "checkpoint.json",
        {"runId": run_id, "mode": mode, "sources": [], "results": {}},
    )
    save(BASE / "active.json", {"run_id": run_id})
    compose(directory, manifest, "up", "-d")
    print(f"Đã tạo {run_id}. Tiếp theo: serve ở cửa sổ 1; run navigation ở cửa sổ 2.")


def environment(directory):
    manifest = read(directory / "manifest.json")
    values = read(directory / "private-env.json")
    assigned = manifest["ports"]
    database = urlparse(values["DATABASE_URL"])
    if (
        database.hostname != "127.0.0.1"
        or database.port != assigned["postgres"]
        or database.path != "/qnu_v1_test_e2e_" + manifest["run_id"]
    ):
        raise RuntimeError("DATABASE_URL không thuộc phiên E2E.")
    for key, service in (
        ("S3_ENDPOINT", "minio"),
        ("QDRANT_URL", "qdrant"),
        ("GOTENBERG_URL", "gotenberg"),
        ("PUBLIC_BASE_URL", "api"),
    ):
        if values[key] != f"http://127.0.0.1:{assigned[service]}":
            raise RuntimeError("Endpoint hạ tầng không thuộc phiên E2E: " + key)
    if (
        values["REDIS_URL"] != f"redis://127.0.0.1:{assigned['redis']}/0"
        or values["S3_BUCKET"] != "qnu-e2e-" + manifest["run_id"]
    ):
        raise RuntimeError("Redis/bucket không thuộc phiên E2E.")
    return {**os.environ, **values}


def wait_http(url, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.5)
    raise RuntimeError("Dịch vụ E2E chưa sẵn sàng: " + url)


@contextmanager
def server_lease(directory):
    """OS releases this lock even when the foreground server is killed."""
    with (directory / "server.lock").open("a+b") as lease:
        if lease.seek(0, os.SEEK_END) == 0:
            lease.write(b"0")
            lease.flush()
        lease.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError(
                    "Serve còn đang chạy; nhấn Ctrl+C ở cửa sổ serve trước."
                ) from exc
        else:
            import fcntl

            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError(
                    "Serve còn đang chạy; nhấn Ctrl+C ở cửa sổ serve trước."
                ) from exc
        try:
            yield
        finally:
            if os.name == "nt":
                lease.seek(0)
                msvcrt.locking(lease.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lease, fcntl.LOCK_UN)


def infrastructure_clients(manifest):
    """Detect leftover local workers without inspecting secrets or killing processes."""
    if os.name != "nt":
        raise RuntimeError(
            "Kiểm tra tiến trình phiên cũ hiện chỉ hỗ trợ Windows; chưa dọn."
        )
    selected = ",".join(
        str(manifest["ports"][name])
        for name in ("postgres", "redis", "minio", "qdrant", "gotenberg")
    )
    script = (
        "$ErrorActionPreference='Stop'; "
        "$taskConnections=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object State -eq Established); "
        f"$taskPorts=@({selected}); "
        "$taskPids=@($taskConnections | Where-Object { "
        "$_.RemoteAddress -in @('127.0.0.1','::1','::ffff:127.0.0.1') -and $_.RemotePort -in $taskPorts "
        "} | Select-Object -ExpandProperty OwningProcess -Unique); "
        "ConvertTo-Json -Compress -InputObject $taskPids"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        raise RuntimeError("Không kiểm tra được kết nối tiến trình; chưa dọn hạ tầng.")
    found = json.loads(result.stdout.strip())
    if not isinstance(found, list) or any(
        type(pid) is not int or pid <= 0 for pid in found
    ):
        raise RuntimeError("Danh sách tiến trình không hợp lệ; chưa dọn.")
    return found


def require_stopped_services(manifest):
    for name in ("api", "frontend", "mock"):
        with socket.socket() as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", manifest["ports"][name])) == 0:
                raise RuntimeError(
                    f"Cổng {name} của phiên còn mở; dừng serve trước khi dọn."
                )
    clients = infrastructure_clients(manifest)
    if clients:
        raise RuntimeError(
            "Còn tiến trình nối vào hạ tầng phiên thử, PID: "
            + ", ".join(map(str, clients))
            + ". Dừng serve/tiến trình của phiên rồi thử lại."
        )


def cleanup(directory, manifest):
    if (directory / "stage.lock").exists():
        raise RuntimeError("Còn stage đang chạy.")
    with server_lease(directory):
        require_stopped_services(manifest)
        # A stale boolean is not proof of a live server. No ports/clients/lease remain.
        save(directory / "server.json", {"running": False})
        compose(directory, manifest, "down", "--volumes", "--remove-orphans")
        manifest["cleaned"] = True
        save(directory / "manifest.json", manifest)
    print("Đã dọn Docker project của phiên; giữ báo cáo cục bộ.")


def serve(directory, manifest):
    with server_lease(directory):
        require_stopped_services(manifest)
        save(directory / "server.json", {"running": True, "phase": "starting"})
        try:
            _serve(directory, manifest)
        finally:
            save(directory / "server.json", {"running": False})


def _serve(directory, manifest):
    if manifest["cleaned"]:
        raise RuntimeError("Phiên đã dọn. Cần init mới.")
    assigned, env = manifest["ports"], environment(directory)
    for name in ("api", "frontend", "mock"):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", assigned[name])) == 0:
                raise RuntimeError(
                    f"Cổng {name} đang được sử dụng; không chiếm tiến trình khác."
                )
    import asyncpg
    import boto3
    from e2e_fixtures import generate_all_fixtures, validate_docx_fixture
    from e2e_mock_server import MockAiServer

    if (directory / "fixtures.json").exists():
        validate_docx_fixture(directory / "fixtures/phu_luc_bang_bieu.docx")

    async def ready():
        for _ in range(90):
            try:
                db = await asyncpg.connect(
                    env["DATABASE_URL"].replace("postgresql+asyncpg", "postgresql")
                )
                await db.close()
                return
            except (OSError, asyncpg.PostgresError):
                await asyncio.sleep(1)
        raise RuntimeError("Database E2E chưa sẵn sàng.")

    asyncio.run(ready())
    subprocess.run(
        [str(PYTHON), "-m", "alembic", "upgrade", "head"], cwd=BE, env=env, check=True
    )
    for url in (
        env["S3_ENDPOINT"] + "/minio/health/live",
        env["QDRANT_URL"] + "/healthz",
        env["GOTENBERG_URL"] + "/health",
    ):
        wait_http(url)
    s3 = boto3.client(
        "s3",
        endpoint_url=env["S3_ENDPOINT"],
        aws_access_key_id=env["S3_ACCESS_KEY"],
        aws_secret_access_key=env["S3_SECRET_KEY"],
    )
    if env["S3_BUCKET"] not in {b["Name"] for b in s3.list_buckets()["Buckets"]}:
        s3.create_bucket(Bucket=env["S3_BUCKET"])
    s3.put_bucket_versioning(
        Bucket=env["S3_BUCKET"], VersioningConfiguration={"Status": "Enabled"}
    )
    if not (directory / "fixtures.json").exists():
        generated = generate_all_fixtures(directory / "fixtures")
        save(
            directory / "fixtures.json",
            {
                name: {
                    "file": file.name,
                    "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                }
                for name, file in generated.items()
            },
        )
    mock = (
        MockAiServer(port=assigned["mock"]) if manifest["mode"] == "workflow" else None
    )
    children, streams = [], []
    backend_sha256 = backend_source_hash()
    try:
        if mock:
            mock.start()
        jobs = [
            (
                [
                    PYTHON,
                    "-m",
                    "uvicorn",
                    "qnu.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(assigned["api"]),
                ],
                BE,
                env,
            ),
            ([PYTHON, "-m", "arq", "qnu.workers.settings.WorkerSettings"], BE, env),
        ]
        fe_env = dict(
            env,
            QNU_API_PROXY_TARGET=env["PUBLIC_BASE_URL"],
            FRONTEND_PORT=str(assigned["frontend"]),
            QNU_DEV_AUTO_LOGIN="true",
            QNU_DEV_ACCESS_KEY=env["DEV_ACCESS_PASSWORD"],
        )
        jobs.append(
            (
                [
                    shutil.which("node"),
                    FE / "node_modules/vite/bin/vite.js",
                    "--port",
                    str(assigned["frontend"]),
                    "--strictPort",
                ],
                FE,
                fe_env,
            )
        )
        for i, (args, cwd, values) in enumerate(jobs):
            stream = (directory / f"service-{i}.log").open("ab")
            streams.append(stream)
            children.append(
                subprocess.Popen(
                    [str(a) for a in args],
                    cwd=cwd,
                    env=values,
                    stdout=stream,
                    stderr=stream,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            )
        wait_http(env["PUBLIC_BASE_URL"] + "/openapi.json")
        with urllib.request.urlopen(
            env["PUBLIC_BASE_URL"] + "/openapi.json"
        ) as response:
            paths = json.load(response)["paths"]
        if not any(p.endswith("/source-deletions/legacy") for p in paths):
            raise RuntimeError("API chưa nạp hợp đồng purge mới.")
        wait_http(f"http://127.0.0.1:{assigned['frontend']}")
        if backend_source_hash() != backend_sha256:
            raise RuntimeError("Mã backend thay đổi trong lúc khởi động. Chạy lại serve.")
        save(
            directory / "server.json",
            {"running": True, "backend_source_sha256": backend_sha256},
        )
        print(
            f"E2E {manifest['mode']}: http://127.0.0.1:{assigned['frontend']}\nGiữ cửa sổ này. Ctrl+C chỉ dừng API/worker/FE thử."
        )
        while all(p.poll() is None for p in children):
            time.sleep(0.5)
        raise RuntimeError("Dịch vụ đã dừng. Xem service-*.log của phiên.")
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        for stream in streams:
            stream.close()
        if mock:
            mock.stop()
        save(directory / "server.json", {"running": False})


def run_stage(directory, manifest, stage, headed, recover=False, skip_review=False):
    state = read(directory / "checkpoint.json")
    model_test = stage in MODEL_STAGES
    admissions_test = stage in ADMISSIONS_STAGES
    if (model_test or admissions_test) and manifest["mode"] != "live":
        print(
            "BLOCKED: model-* và admissions-* cần phiên init --mode live, không dùng AI giả lập."
        )
        return 2
    sequence = MODEL_STAGES if model_test else ADMISSIONS_STAGES if admissions_test else STAGES
    index = sequence.index(stage)
    if model_test:
        prerequisites = [] if stage == "provider-setup" else ["provider-setup"]
        if stage != "provider-setup" and stage != "model-discovery":
            prerequisites.append("model-discovery")
    else:
        prerequisites = (
            ("navigation", *(s for s in ADMISSIONS_STAGES[:index] if s != "admissions-draft"))
            if admissions_test
            else STAGES[:index]
        )
    if manifest["mode"] == "live" and not model_test:
        prerequisites = (*MODEL_STAGES, *prerequisites)
    fast_publication = skip_review and stage == "admissions-publication"
    fast_chat = stage == "admissions-chat" and state["results"].get("admissions-publication", {}).get("review_mode") == "skipped"
    if fast_publication or fast_chat:
        prerequisites = tuple(x for x in prerequisites if x != "admissions-compilation") + ("admissions-draft",)
    missing = [
        x for x in prerequisites if state["results"].get(x, {}).get("status") != "PASS"
    ]
    if state.get("consumed") and not model_test:
        print("BLOCKED: phiên đã hoàn tất purge; tạo phiên E2E mới để chạy lại.")
        return 2
    if missing:
        print("BLOCKED: cần chạy đạt các chặng trước: " + ", ".join(missing))
        return 2
    server = read(directory / "server.json") if (directory / "server.json").exists() else {}
    if not server.get("running"):
        print("BLOCKED: chạy serve ở cửa sổ khác trước.")
        return 2
    if server.get("phase") == "starting":
        print("BLOCKED: serve đang khởi động; chờ dòng E2E live/workflow rồi chạy lại.")
        return 2
    if server.get("backend_source_sha256") != backend_source_hash():
        print(
            "BLOCKED: API/worker chưa xác nhận mã backend hiện tại. "
            "Nhấn Ctrl+C tại cửa sổ serve, chạy lại .\\test-v1-e2e.ps1 serve "
            "rồi chạy lại chặng. Không cleanup/init."
        )
        return 2
    lock = directory / "stage.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(
            "Còn stage.lock; kiểm tra lệnh trước đã dừng trước khi gỡ khóa."
        ) from None
    try:
        os.close(fd)
        output = directory / "runs" / f"{stage}-{time.time_ns()}"
        output.mkdir(parents=True)
        env = dict(
            environment(directory),
            E2E_STAGE=stage,
            E2E_SESSION=str(directory),
            E2E_OUTPUT=str(output),
            E2E_BASE_URL=f"http://127.0.0.1:{manifest['ports']['frontend']}",
            E2E_MODEL_PROFILE=str(ROOT / "scripts/e2e_profiles/qnu-server.json"),
        )
        if recover:
            # Explicit operator choice: replace a terminal compilation run with a
            # new one built from the completed OCR source. Never a silent retry.
            env["E2E_RECOVER_COMPILATION"] = "1"
        # An inherited shell value must not silently change the reviewed workflow.
        env["E2E_SKIP_REVIEW"] = "1" if fast_publication else "0"
        args = [
            shutil.which("node"),
            FE / "node_modules/@playwright/test/cli.js",
            "test",
            "--project=desktop-chromium",
        ]
        if headed:
            args.append("--headed")
        if stage == "provider-setup":
            from e2e_provider_setup import prepare_provider

            try:
                prepare_provider(
                    directory, env, ROOT / "scripts/e2e_profiles/qnu-server.json"
                )
            except RuntimeError as exc:
                state = read(directory / "checkpoint.json")
                state["results"][stage] = {
                    "status": "BLOCKED",
                    "exit_code": 2,
                    "report": str(output),
                }
                for dependent in (*MODEL_STAGES[1:], *STAGES, *ADMISSIONS_STAGES):
                    state["results"].pop(dependent, None)
                save(directory / "checkpoint.json", state)
                print("BLOCKED:", exc)
                return 2
        result = subprocess.run([str(a) for a in args], cwd=FE, env=env, check=False)
        verdict = "FAIL"
        report_file = output / "results.json"
        if report_file.exists():
            report = read(report_file)
            stats = report.get("stats", {})
            if (
                result.returncode == 0
                and stats.get("expected") == 1
                and not any(
                    stats.get(key, 0) for key in ("unexpected", "skipped", "flaky")
                )
            ):
                verdict = "PASS"
            elif "BLOCKED:" in json.dumps(report):
                verdict = "BLOCKED"
        exit_code = 0 if verdict == "PASS" else result.returncode or 2
        state = read(directory / "checkpoint.json")
        state["results"][stage] = {
            "status": verdict,
            "exit_code": exit_code,
            "at": datetime.now(UTC).isoformat(),
            "report": str(output),
        }
        if fast_publication:
            state["results"][stage]["review_mode"] = "skipped"
        if model_test:
            dependents = (
                (*MODEL_STAGES[index + 1 :], *STAGES, *ADMISSIONS_STAGES)
                if stage in {"provider-setup", "model-discovery"}
                else (*STAGES, *ADMISSIONS_STAGES)
            )
        else:
            dependents = sequence[index + 1 :]
            if stage == "navigation":
                dependents = (*dependents, *ADMISSIONS_STAGES)
        for dependent in dependents:
            state["results"].pop(dependent, None)
        if stage == "lifecycle" and verdict == "PASS":
            state["consumed"] = True
        save(directory / "checkpoint.json", state)
        print(stage, state["results"][stage]["status"], "→", output)
        return exit_code
    finally:
        lock.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="init → serve (cửa sổ 1); run <stage>/all (cửa sổ 2); Ctrl+C serve → cleanup"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=(
            "help",
            "init",
            "serve",
            "run",
            "all",
            "models",
            "status",
            "report",
            "cleanup",
        ),
    )
    parser.add_argument("stage", nargs="?", choices=STAGES + MODEL_STAGES + ADMISSIONS_STAGES)
    parser.add_argument("--session")
    parser.add_argument("--mode", choices=("workflow", "live"), default="workflow")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument(
        "--recover",
        action="store_true",
        help="Cho phép thay lượt biên soạn đã kết thúc bằng lượt mới từ nguồn OCR đã xong.",
    )
    parser.add_argument("--skip-review", action="store_true", help="Xuất bản nhanh bản nháp E2E, ghi rõ bỏ qua model review.")
    args = parser.parse_args(argv)
    if args.skip_review and (args.command != "run" or args.stage != "admissions-publication"):
        parser.error("--skip-review chỉ áp dụng cho run admissions-publication")
    try:
        if args.command == "help":
            parser.print_help()
        elif args.command == "init":
            initialize(args.mode)
        else:
            directory, manifest = load_session(args.session)
            if args.command == "serve":
                serve(directory, manifest)
            elif args.command in {"run", "all", "models"}:
                if args.command == "run" and not args.stage:
                    parser.error("run cần tên chặng")
                sequence = (
                    MODEL_STAGES
                    if args.command == "models"
                    else STAGES
                    if args.command == "all"
                    else [args.stage]
                )
                for stage in sequence:
                    code = run_stage(directory, manifest, stage, args.headed, args.recover, args.skip_review)
                    if code:
                        return code
            elif args.command in {"status", "report"}:
                state = read(directory / "checkpoint.json")
                print("Phiên:", manifest["run_id"], "Mode:", manifest["mode"])
                for stage in STAGES + (
                    MODEL_STAGES if manifest["mode"] == "live" else ()
                ) + (
                    ADMISSIONS_STAGES if state.get("admissions") else ()
                ):
                    row = state["results"].get(stage, {})
                    print(stage, row.get("status", "NOT RUN"), row.get("report", ""))
            elif args.command == "cleanup":
                cleanup(directory, manifest)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(
            "BLOCKED:",
            str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__,
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
