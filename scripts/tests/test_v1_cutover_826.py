"""Default entrypoints must select V1 without starting services or changing data."""

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "cutover_runner", ROOT / "scripts/run_v1.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class CutoverTests(unittest.TestCase):
    def test_combined_tests_stop_after_backend_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").touch()
            with (
                patch.object(runner, "ROOT", root),
                patch.object(runner.shutil, "which", side_effect=lambda value: value),
                patch.object(
                    runner.subprocess, "run", return_value=Mock(returncode=7)
                ) as run,
            ):
                self.assertEqual(runner.main(["test", "--env-dir", "root"]), 7)
                self.assertEqual(run.call_count, 1)
                self.assertIn("run_isolated_tests.py", run.call_args.args[0][-1])

    def test_e2e_arguments_go_to_existing_staged_runner(self):
        with patch.object(
            runner.subprocess, "run", return_value=Mock(returncode=3)
        ) as run:
            self.assertEqual(runner.main(["e2e", "status"]), 3)
            self.assertEqual(Path(run.call_args.args[0][1]).name, "v1_e2e_runner.py")
            self.assertEqual(run.call_args.args[0][-1], "status")

    def test_default_dev_plan_is_v1_and_does_not_migrate(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(runner.main(["dev", "--dry-run"]), 0)
        plan = json.loads(output.getvalue())
        commands = [part for step in plan for part in step["argv"]]
        self.assertIn("qnu.main:app", commands)
        self.assertIn("qnu.workers.settings.WorkerSettings", commands)
        self.assertNotIn("alembic", commands)
        self.assertTrue(any("frontendV1" in step["cwd"] for step in plan))

    def test_short_build_and_prefixed_build_have_identical_plans(self):
        results = []
        for command in ("build", "v1-build"):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(runner.main([command, "--dry-run"]), 0)
            results.append(json.loads(output.getvalue()))
        self.assertEqual(results[0], results[1])

    def test_removed_legacy_writes_fail_without_any_subprocess(self):
        for command in ("seed", "reset-db", "reseed", "reindex", "reconcile"):
            with (
                self.subTest(command=command),
                patch.object(runner.subprocess, "run") as run,
                patch.object(runner.subprocess, "Popen") as popen,
                contextlib.redirect_stderr(io.StringIO()),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(runner.main([command]), 2)
                run.assert_not_called()
                popen.assert_not_called()

    def test_default_wrappers_do_not_contain_legacy_paths(self):
        for name in (
            "make",
            "make.ps1",
            "make.bat",
            "Makefile",
            "run.ps1",
            "scripts/start-dev.ps1",
            "scripts/start-worker.ps1",
            "scripts/start-dev-service.ps1",
        ):
            with self.subTest(name=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                for forbidden in (
                    "app.main:app",
                    "app.cli",
                    "cd backend",
                    "cd frontend",
                    "backend\\.venv",
                    '"backend"',
                    '"frontend"',
                ):
                    self.assertNotIn(forbidden, source)

    def test_production_compose_builds_v1_and_migrates_without_seed(self):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(ROOT / ".env.dokploy.example"),
                "-f",
                str(ROOT / "docker-compose.yml"),
                "config",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            "Compose validation failed; inspect locally without printing env",
        )
        services = json.loads(result.stdout)["services"]
        backend = services["backend"]
        self.assertEqual(Path(backend["build"]["context"]).name, "backendV1")
        self.assertEqual(
            Path(services["frontend"]["build"]["context"]).name, "frontendV1"
        )
        self.assertIn("qnu.main:app", backend["command"])
        self.assertEqual(
            services["bootstrap"]["command"], ["alembic", "upgrade", "head"]
        )
        self.assertIn(
            "qnu.workers.settings.WorkerSettings", services["worker"]["command"]
        )
        self.assertEqual(backend["environment"]["QUEUE_NAME"], "qnu:v1:jobs")
        self.assertEqual(backend["environment"]["DEV_AUTH_ENABLED"], "false")
        self.assertEqual(
            services["frontend"]["build"]["args"]["VITE_DEV_AUTH_ENABLED"], "false"
        )

    def test_nginx_preserves_api_paths_and_waits_for_long_model_calls(self):
        config = (ROOT / "frontendV1/nginx.conf").read_text(encoding="utf-8")
        self.assertIn("location /platform/v1alpha1", config)
        self.assertIn("proxy_pass http://backend:8002;", config)
        self.assertIn("proxy_buffering off;", config)
        self.assertIn("proxy_read_timeout 86400s;", config)


if __name__ == "__main__":
    unittest.main()
