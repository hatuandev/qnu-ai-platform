"""Run the nine failed admission cases in a fresh report without editing checkpoints."""

import argparse
import os
import shutil
import subprocess
import sys
import time

import v1_e2e_session as runner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    directory, manifest = runner.load_session()
    server = runner.read(directory / "server.json")
    if (
        not server.get("running")
        or server.get("backend_source_sha256") != runner.backend_source_hash()
    ):
        raise RuntimeError(
            "BLOCKED: serve chưa nạp backend hiện tại; chạy serve cùng phiên trước."
        )
    state = runner.read(directory / "checkpoint.json")
    if (
        state.get("results", {}).get("admissions-publication", {}).get("status")
        != "PASS"
    ):
        raise RuntimeError("BLOCKED: publication/index chưa PASS.")
    lock = directory / "stage.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        output = directory / "runs" / f"admissions-retest9-{time.time_ns()}"
        output.mkdir(parents=True, exist_ok=False)
        env = dict(
            runner.environment(directory),
            E2E_STAGE="admissions-chat",
            E2E_RETEST9="true",
            E2E_SESSION=str(directory),
            E2E_OUTPUT=str(output),
            E2E_BASE_URL=f"http://127.0.0.1:{manifest['ports']['frontend']}",
            E2E_MODEL_PROFILE=str(runner.ROOT / "scripts/e2e_profiles/qnu-server.json"),
        )
        command = [
            shutil.which("node"),
            str(runner.FE / "node_modules/@playwright/test/cli.js"),
            "test",
            "--config",
            str(runner.FE / "playwright.retest9.config.ts"),
            "--project=desktop-chromium",
        ]
        if args.headed:
            command.append("--headed")
        print("Report:", output, flush=True)
        result = subprocess.run(command, cwd=runner.FE, env=env, check=False)
        report_file = output / "retest9-answers.json"
        if not report_file.exists():
            return result.returncode or 1
        report = runner.read(report_file)
        failed = any(
            report.get(key) for key in ("failed", "not_run", "uncertain", "halted")
        )
        complete = (
            report.get("passed")
            == report.get("dispatched")
            == report.get("expected")
            == 9
        )
        print(
            "Result:",
            {
                k: report.get(k)
                for k in ("passed", "failed", "not_run", "uncertain", "halted")
            },
            flush=True,
        )
        return result.returncode or (1 if failed or not complete else 0)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, FileExistsError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
