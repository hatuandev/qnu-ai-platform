"""Default QNU task runner: V1 only, foreground services, explicit data operations."""

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
    "v1-dev": "API 8002 + worker + FE 3001; Ctrl+C stops this session",
    "v1-be": "API only, foreground, port 8002",
    "v1-worker": "ARQ worker only, foreground, V1 queue",
    "v1-fe": "Frontend only, foreground, port from frontendV1/.env.local",
    "v1-check": "Read-only dependency/schema/frontend check before startup",
    "v1-infra-up": "Start PostgreSQL/Redis/Qdrant/MinIO/Gotenberg; prepare and verify local storage",
    "v1-infra-down": "Stop local infrastructure, preserve volumes",
    "v1-clear": "Delete local Docker data volumes (requires --confirm-local-reset)",
    "v1-seed-modelops": "Configure QNU model defaults in the local development database",
    "v1-infra-status": "Show local infrastructure containers",
    "v1-infra-logs": "Follow local infrastructure logs",
    "v1-install-be": "Install backend dependencies from uv.lock",
    "v1-install-fe": "Install frontend dependencies from package-lock.json",
    "v1-migrate": "Explicit Alembic upgrade head; check target DB first",
    "v1-db-check": "Read current Alembic revision; no migration or seed",
    "v1-test-be": "Backend isolated-DB harness; creates/deletes its test DB",
    "v1-test-fe": "Frontend Vitest suite",
    "v1-test": "Isolated backend tests then frontend tests; stop on failure",
    "v1-test-e2e": "Show staged E2E help; use make.ps1 v1-e2e init/serve/run <stage>",
    "v1-lint": "Backend Ruff then frontend Biome; no automatic fixes",
    "v1-lint-fix": "Explicit Ruff/Biome fixes, V1 source only",
    "v1-typecheck": "Frontend TypeScript; run dev/build first on a fresh clone",
    "v1-build": "Frontend build including TypeScript",
    "v1-help": "Show V1 commands",
}

ALIASES = {name.removeprefix("v1-"): name for name in COMMANDS}
ALIASES.update(
    {"dev1": "v1-dev", "dev2": "v1-dev", "fe2": "v1-fe", "db-ready": "v1-check"}
)
REMOVED_COMMANDS = {"seed", "reset-db", "reseed", "reconcile", "reindex"}


def command_plan(
    command: str, root: Path, env_dir: str
) -> list[tuple[Path, list[str]]]:
    backend = root / "backendV1"
    frontend = root / "frontendV1"
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
    fe = (frontend, ["node", str(frontend / "node_modules/vite/bin/vite.js")])
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
        "v1-dev": [check, api, worker, fe],
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
        "v1-fe": [fe],
        "v1-install-be": [(backend, ["uv", "sync", "--extra", "dev", "--frozen"])],
        "v1-install-fe": [
            (frontend, ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"])
        ],
        "v1-migrate": [(backend, [*migration, "upgrade", "head"])],
        "v1-db-check": [(backend, [*migration, "current"])],
        "v1-test-be": [
            (runtime, [*uv, "python", str(backend / "scripts/run_isolated_tests.py")])
        ],
        "v1-test-fe": [(frontend, ["npm", "test"])],
        "v1-test-e2e": [
            (root, [*uv, "python", str(root / "scripts/v1_e2e_runner.py")])
        ],
        "v1-lint": [
            (backend, [*uv, "ruff", "check", "."]),
            (frontend, ["npm", "run", "lint"]),
        ],
        "v1-lint-fix": [
            (backend, [*uv, "ruff", "check", "--fix", "."]),
            (frontend, ["npm", "run", "lint:fix"]),
        ],
        "v1-typecheck": [(frontend, ["npm", "run", "typecheck"])],
        "v1-build": [(frontend, ["npm", "run", "build"])],
    }
    plans["v1-test"] = [*plans["v1-test-be"], *plans["v1-test-fe"]]
    return plans[command]


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
    if selected in {"e2e", "v1-e2e"}:
        # Keep the staged runner's argument/approval and credential boundaries.
        command = [sys.executable, str(ROOT / "scripts/v1_e2e_runner.py"), *argv[1:]]
        return subprocess.run(command, cwd=ROOT, check=False).returncode
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
            "QNU V1 is the default: make dev/check/build; v1-* aliases remain available."
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
        executable = shutil.which(command[0])
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
        if args.command == "v1-dev":
            print("Checking V1 dependencies before starting services...", flush=True)
            cwd, check = plan[0]
            code = subprocess.run(check, cwd=cwd, check=False).returncode
            if code:
                return code
            print(
                "Starting V1 API/worker/FE in foreground. Ctrl+C stops only this session.",
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
