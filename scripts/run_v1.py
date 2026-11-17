"""QNU task runner for Backend V1 and the local Frontend V2 workflows."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    "v2-dev": "Default dev: API V1 8002 + worker V1 + FE V2 3002",
    "v2-fe": "Frontend V2 only, foreground, port 3002",
    "v2-check": "Default check: read-only dependencies, V1 schema and FE V2",
    "v2-install-fe": "Install Frontend V2 dependencies from package-lock.json",
    "v2-typecheck": "Frontend V2 TypeScript; run dev/build first on a fresh clone",
    "v2-build": "Frontend V2 build including TypeScript",
    "v1-dev": "API V1 8002 + worker V1; backend only, no frontend",
    "v1-be": "API only, foreground, port 8002",
    "v1-worker": "ARQ worker only, foreground, V1 queue",
    "v1-check": "Read-only dependency/schema/frontend check before startup",
    "v1-infra-up": "Start PostgreSQL/Redis/Qdrant/MinIO/Gotenberg; prepare and verify local storage",
    "v1-infra-down": "Stop local infrastructure, preserve volumes",
    "v1-clear": "Delete local Docker data volumes (requires --confirm-local-reset)",
    "v1-seed-modelops": "Configure QNU model defaults in the local development database",
    "v1-infra-status": "Show local infrastructure containers",
    "v1-infra-logs": "Follow local infrastructure logs",
    "v1-install-be": "Install backend dependencies from uv.lock",
    "v1-migrate": "Explicit Alembic upgrade head; check target DB first",
    "v1-db-check": "Read current Alembic revision; no migration or seed",
    "v1-test-be": "Backend isolated-DB harness; creates/deletes its test DB",
    "v1-test": "Isolated backend tests; Frontend V2 has no test suite",
    "v1-lint": "Backend Ruff then Frontend V2 Biome; no automatic fixes",
    "v1-lint-fix": "Explicit Ruff/Biome fixes, backend and Frontend V2 source",
    "v1-help": "Show QNU runner commands",
}

ALIASES = {
    name.removeprefix("v1-"): name for name in COMMANDS if name.startswith("v1-")
}
ALIASES.update(
    {
        "dev": "v2-dev",
        "dev2": "v2-dev",
        "fe": "v2-fe",
        "fe2": "v2-fe",
        "check": "v2-check",
        "db-ready": "v2-check",
        "install-fe": "v2-install-fe",
        "typecheck": "v2-typecheck",
        "build": "v2-build",
    }
)
REMOVED_COMMANDS = {"seed", "reset-db", "reseed", "reconcile", "reindex"}


def command_plan(
    command: str, root: Path, env_dir: str
) -> list[tuple[Path, list[str]]]:
    backend = root / "backendV1"
    frontend_v2 = root / "frontendV2"
    runtime = root if env_dir == "root" else backend
    uv = ["uv", "run", "--project", str(backend), "--frozen", "--extra", "dev"]
    service_uv = [*uv, "--no-sync"]
    api = (
        runtime,
        [
            *service_uv,
            "uvicorn",
            "qnu.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",
        ],
    )
    worker = (runtime, [*service_uv, "arq", "qnu.workers.settings.WorkerSettings"])
    # Avoid npm.cmd's interactive "Terminate batch job?" during Ctrl+C on Windows.
    fe_v2 = (
        frontend_v2,
        [
            "node",
            str(frontend_v2 / "node_modules/vite/bin/vite.js"),
            "--port",
            "3002",
            "--strictPort",
        ],
    )
    check = (runtime, [*uv, "python", str(root / "scripts/check_v1_runtime.py")])
    # Alembic paths are relative to backendV1; explicitly load root env for mode A.
    migration = [
        *uv,
        *(["--env-file", (root / ".env").as_posix()] if env_dir == "root" else []),
        "alembic",
    ]
    infra = [
        "docker",
        "compose",
        "-f",
        str(root / "docker-compose.infra.yml"),
        "--env-file",
        str(runtime / ".env"),
    ]
    plans = {
        "v2-dev": [check, api, worker, fe_v2],
        "v2-check": [check],
        "v2-fe": [fe_v2],
        "v2-install-fe": [
            (frontend_v2, ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"])
        ],
        "v2-typecheck": [(frontend_v2, ["npm", "run", "typecheck"])],
        "v2-build": [(frontend_v2, ["npm", "run", "build"])],
        "v1-dev": [check, api, worker],
        "v1-check": [check],
        "v1-infra-down": [(root, [*infra, "down"])],
        "v1-clear": [(root, [*infra, "down", "--volumes"])],
        "v1-seed-modelops": [
            (runtime, [*uv, "python", str(backend / "scripts/seed_local_modelops.py")])
        ],
        "v1-infra-status": [(root, [*infra, "ps"])],
        "v1-infra-logs": [(root, [*infra, "logs", "-f"])],
        "v1-infra-up": [
            (
                runtime,
                [*uv, "python", str(root / "scripts/v1_storage.py"), "--validate"],
            ),
            (
                root,
                [
                    "docker",
                    "compose",
                    "-f",
                    str(root / "docker-compose.infra.yml"),
                    "--env-file",
                    str(runtime / ".env"),
                    "up",
                    "-d",
                    "--wait",
                    "postgres",
                    "redis",
                    "qdrant",
                    "minio",
                    "gotenberg",
                ],
            ),
            (
                runtime,
                [
                    *service_uv,
                    "python",
                    str(root / "scripts/v1_storage.py"),
                    "--prepare-local",
                ],
            ),
        ],
        "v1-be": [api],
        "v1-worker": [worker],
        "v1-install-be": [(backend, ["uv", "sync", "--extra", "dev", "--frozen"])],
        "v1-migrate": [(backend, [*migration, "upgrade", "head", "--tag", "qnu-bootstrap"])],
        "v1-db-check": [(backend, [*migration, "current"])],
        "v1-test-be": [
            (runtime, [*uv, "python", str(backend / "scripts/run_isolated_tests.py")])
        ],
        "v1-lint": [
            (backend, [*uv, "ruff", "check", "."]),
            (frontend_v2, ["npm", "run", "lint"]),
        ],
        "v1-lint-fix": [
            (backend, [*uv, "ruff", "check", "--fix", "."]),
            (frontend_v2, ["npm", "run", "lint:fix"]),
        ],
    }
    plans["v1-test"] = [*plans["v1-test-be"]]
    return plans[command]


def resolve_executable(command_name: str) -> str | None:
    """Find executable, prioritizing PATHEXT on Windows to avoid matching POSIX scripts."""
    if os.name == "nt":
        pathext = [ext for ext in (os.environ.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD").split(";") if ext]
        for ext in pathext:
            target = command_name if command_name.lower().endswith(ext.lower()) else f"{command_name}{ext}"
            found = shutil.which(target)
            if found:
                return found
    return shutil.which(command_name)


def stop_services(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            try:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                continue  # Child exited between poll and signal.
    deadline = time.monotonic() + 10
    for process in processes:
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False
                )
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def process_environment(command: list[str]) -> dict[str, str]:
    environment = dict(os.environ)
    if "qnu.main:app" in command:
        # Root .env may belong to legacy; match the actual V1 uvicorn port in logs.
        environment["PORT"] = "8002"
    return environment


def run_services(plan: list[tuple[Path, list[str]]]) -> int:
    processes: list[subprocess.Popen] = []
    try:
        for cwd, args in plan:
            options = (
                {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            processes.append(
                subprocess.Popen(
                    args, cwd=cwd, env=process_environment(args), **options
                )
            )
        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    print(
                        f"V1 service exited ({code}); stopping the other services of this session.",
                        file=sys.stderr,
                    )
                    return code or 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 130
    finally:
        stop_services(processes)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    selected = argv[0] if argv else "help"
    if selected in REMOVED_COMMANDS:
        print(
            f"'{selected}' belongs to the retired backend and is not a V1 command. "
            "Use ModelOps/knowledge operations in the V1 UI; no data was changed.",
            file=sys.stderr,
        )
        return 2
    if argv:
        argv[0] = ALIASES.get(selected, selected)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS, nargs="?", default="v1-help")
    parser.add_argument(
        "--env-dir",
        choices=("root", "backend"),
        default=os.environ.get("QNU_V1_ENV_DIR", "root"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print argv/cwd only; never read env values or run commands",
    )
    parser.add_argument("--confirm-local-reset", action="store_true")
    args = parser.parse_args(argv)
    if args.env_dir not in {"root", "backend"}:
        parser.error("QNU_V1_ENV_DIR must be root or backend")
    if args.command == "v1-help":
        print(
            "make dev (or dev2) starts Backend V1, its worker and Frontend V2. "
            "Backend only: make v1-dev."
        )
        for name, description in COMMANDS.items():
            print(f"  make {name:<16} {description}")
        print("Default env: root .env. Set QNU_V1_ENV_DIR=backend for backendV1/.env.")
        print(
            "Use --dry-run to inspect; services do not migrate/seed/restart existing processes."
        )
        return 0
    plan = command_plan(args.command, ROOT, args.env_dir)
    if args.dry_run:
        print(
            json.dumps(
                [{"cwd": str(cwd), "argv": argv} for cwd, argv in plan], indent=2
            )
        )
        return 0
    if args.command == "v1-clear" and not args.confirm_local_reset:
        parser.error("clear deletes local data volumes; pass --confirm-local-reset")
    if args.command in {
        "v2-dev",
        "v2-check",
        "v1-dev",
        "v1-check",
        "v1-be",
        "v1-worker",
        "v1-migrate",
        "v1-db-check",
        "v1-test-be",
        "v1-test",
        "v1-infra-up",
        "v1-infra-down",
        "v1-clear",
        "v1-seed-modelops",
        "v1-infra-status",
        "v1-infra-logs",
    }:
        env_path = (ROOT if args.env_dir == "root" else ROOT / "backendV1") / ".env"
        if not env_path.is_file():
            parser.error(
                f"Missing {env_path}. Configure it first; see docs/quy_trinh/38_huong_dan_chay_qnu_v1.md"
            )
    # Resolve ALL tools before starting any service.
    for _, command in plan:
        executable = resolve_executable(command[0])
        if not executable:
            parser.error(f"Required command not found: {command[0]}")
        command[0] = executable
    try:
        if args.command == "v1-clear":
            docker = plan[0][1][0]
            context = os.environ.get("DOCKER_CONTEXT")
            endpoint = None if context else os.environ.get("DOCKER_HOST")
            if not endpoint:
                result = subprocess.run(
                    [
                        docker, "context", "inspect", "--format",
                        "{{.Endpoints.docker.Host}}",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                endpoint = result.stdout.strip() if result.returncode == 0 else ""
            if not endpoint.startswith(("unix:///", "npipe:////./pipe/")):
                print("clear requires a local Docker socket or pipe.", file=sys.stderr)
                return 1
        if args.command in {"v1-dev", "v2-dev"}:
            print("Checking Backend V1 dependencies...", flush=True)
            cwd, check = plan[0]
            code = subprocess.run(check, cwd=cwd, check=False).returncode
            if code:
                return code
            frontend_note = " and Frontend V2" if args.command == "v2-dev" else ""
            print(
                f"Starting V1 API/worker{frontend_note} in foreground. "
                "Ctrl+C stops only this session.",
                flush=True,
            )
            return run_services(plan[1:])
        for cwd, command in plan:
            code = subprocess.run(
                command, cwd=cwd, env=process_environment(command), check=False
            ).returncode
            if code:
                return code
        return 0
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        print(f"V1 command could not start: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
