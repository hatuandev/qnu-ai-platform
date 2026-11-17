"""Runner boundary tests: no database, model or application service is started."""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "run_v1", Path(__file__).parents[1] / "run_v1.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def test_seed_modelops_uses_selected_app_environment(self):
        for mode in ("root", "backend"):
            [(cwd, argv)] = runner.command_plan("v1-seed-modelops", runner.ROOT, mode)
            self.assertEqual(cwd, runner.ROOT if mode == "root" else runner.ROOT / "backendV1")
            self.assertEqual(Path(argv[-1]).name, "seed_local_modelops.py")

    def test_clear_requires_explicit_confirmation(self):
        with (
            patch.object(runner.subprocess, "run") as run,
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as error,
        ):
            runner.main(["clear"])
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()

    def test_clear_limits_compose_to_selected_local_stack(self):
        [(cwd, argv)] = runner.command_plan("v1-clear", runner.ROOT, "backend")
        self.assertEqual(cwd, runner.ROOT)
        self.assertEqual(Path(argv[argv.index("-f") + 1]).name, "docker-compose.infra.yml")
        self.assertEqual(Path(argv[argv.index("--env-file") + 1]).parent.name, "backendV1")
        self.assertEqual(argv[-2:], ["down", "--volumes"])

    def test_clear_rejects_remote_docker(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(runner, "ROOT", Path(directory)),
            patch.object(runner.shutil, "which", return_value="docker"),
            patch.dict(runner.os.environ, {"DOCKER_HOST": "ssh://remote"}, clear=True),
            patch.object(runner.subprocess, "run") as run,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            (Path(directory) / ".env").touch()
            self.assertEqual(runner.main(["clear", "--confirm-local-reset"]), 1)
        run.assert_not_called()

    def test_infra_validation_failure_prevents_docker_and_bucket_setup(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(runner.shutil, "which", side_effect=lambda name: name),
            patch.object(
                runner.subprocess, "run", return_value=Mock(returncode=1)
            ) as run,
        ):
            root = Path(directory)
            (root / ".env").touch()
            with patch.object(runner, "ROOT", root):
                self.assertEqual(runner.main(["v1-infra-up", "--env-dir", "root"]), 1)
            self.assertEqual(run.call_count, 1)
            self.assertIn("--validate", run.call_args.args[0])

    def test_infra_docker_failure_prevents_bucket_setup(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(runner.shutil, "which", side_effect=lambda name: name),
            patch.object(
                runner.subprocess,
                "run",
                side_effect=[
                    Mock(returncode=0),
                    Mock(returncode=17),
                ],
            ) as run,
        ):
            root = Path(directory)
            (root / ".env").touch()
            with patch.object(runner, "ROOT", root):
                self.assertEqual(runner.main(["v1-infra-up", "--env-dir", "root"]), 17)
            self.assertEqual(run.call_count, 2)

    def test_infra_uses_selected_env_starts_storage_then_initializes_bucket(self):
        for mode in ("root", "backend"):
            plan = runner.command_plan("v1-infra-up", runner.ROOT, mode)
            runtime = runner.ROOT if mode == "root" else runner.ROOT / "backendV1"
            self.assertEqual(len(plan), 3)
            self.assertIn("--validate", plan[0][1])
            _, compose = plan[1]
            self.assertEqual(
                Path(compose[compose.index("--env-file") + 1]), runtime / ".env"
            )
            self.assertEqual(
                compose[-5:], ["postgres", "redis", "qdrant", "minio", "gotenberg"]
            )
            self.assertIn("--wait", compose)
            self.assertIn("--prepare-local", plan[2][1])
            self.assertEqual(plan[2][0], runtime)

    def test_successful_preflight_starts_only_three_services(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(runner.shutil, "which", side_effect=lambda name: name),
            patch.object(
                runner.subprocess, "run", return_value=Mock(returncode=0)
            ) as check,
            patch.object(runner, "run_services", return_value=0) as services,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            root = Path(directory)
            (root / ".env").touch()
            with patch.object(runner, "ROOT", root):
                self.assertEqual(runner.main(["dev", "--env-dir", "root"]), 0)
            check.assert_called_once()
            self.assertEqual(
                Path(check.call_args.args[0][-1]).name, "check_v1_runtime.py"
            )
            [api, worker, frontend] = services.call_args.args[0]
            self.assertIn("qnu.main:app", api[1])
            self.assertIn("qnu.workers.settings.WorkerSettings", worker[1])
            self.assertEqual(frontend[0], root / "frontendV2")
            self.assertEqual(frontend[1][-3:], ["--port", "3002", "--strictPort"])

    def test_frontend_aliases_match_their_dev_workflows(self):
        for alias, directory, command in (
            ("dev", "frontendV2", "v2-dev"),
            ("dev2", "frontendV2", "v2-dev"),
            ("fe", "frontendV2", "v2-fe"),
            ("fe2", "frontendV2", "v2-fe"),
        ):
            with (
                self.subTest(alias=alias),
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(runner.main([alias, "--dry-run"]), 0)
                plan = json.loads(output.getvalue())
                self.assertEqual(Path(plan[-1]["cwd"]).name, directory)
                self.assertEqual(runner.ALIASES[alias], command)

    def test_uv_env_file_uses_windows_safe_forward_slashes(self):
        _, command = runner.command_plan("v1-migrate", runner.ROOT, "root")[0]
        path = command[command.index("--env-file") + 1]
        self.assertNotIn("\\", path)
        self.assertEqual(Path(path), runner.ROOT / ".env")

    def test_preflight_failure_blocks_all_services(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(runner.shutil, "which", side_effect=lambda name: name),
            patch.object(runner.subprocess, "run", return_value=Mock(returncode=1)),
            patch.object(runner, "run_services", return_value=0) as services,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            root = Path(directory)
            (root / ".env").touch()
            with patch.object(runner, "ROOT", root):
                self.assertEqual(runner.main(["v1-dev", "--env-dir", "root"]), 1)
            services.assert_not_called()

    def test_dev_has_one_sync_then_no_sync_service_commands(self):
        plan = runner.command_plan("v2-dev", runner.ROOT, "root")
        self.assertEqual(len(plan), 4)
        self.assertNotIn("--no-sync", plan[0][1])
        for _, command in plan[1:3]:
            self.assertIn("--no-sync", command)
        self.assertEqual(plan[-1][1][0], "node")

    def test_api_port_environment_matches_listener_without_mutating_parent(self):
        with patch.dict(os.environ, {"PORT": "8001"}):
            environment = runner.process_environment(["uvicorn", "qnu.main:app"])
            self.assertEqual(environment["PORT"], "8002")
            self.assertEqual(os.environ["PORT"], "8001")

    def test_every_dry_run_is_side_effect_free_and_explicit(self):
        for command in runner.COMMANDS:
            if command == "v1-help":
                continue
            with (
                self.subTest(command=command),
                patch.object(runner.subprocess, "run") as run,
                patch.object(runner.subprocess, "Popen") as popen,
                contextlib.redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(
                    runner.main([command, "--dry-run", "--env-dir", "root"]), 0
                )
                plan = json.loads(output.getvalue())
                self.assertTrue(plan)
                run.assert_not_called()
                popen.assert_not_called()

    def test_dev_uses_v1_paths_and_does_not_migrate_or_seed(self):
        for mode in ("root", "backend"):
            plan = runner.command_plan("v2-dev", runner.ROOT, mode)
            self.assertEqual(len(plan), 4)
            runtime = runner.ROOT if mode == "root" else runner.ROOT / "backendV1"
            self.assertEqual(
                [cwd for cwd, _ in plan],
                [runtime, runtime, runtime, runner.ROOT / "frontendV2"],
            )
            args = [arg for _, command in plan for arg in command]
            self.assertIn("qnu.main:app", args)
            self.assertIn("qnu.workers.settings.WorkerSettings", args)
            self.assertIn("8002", args)
            self.assertTrue(
                set(args).isdisjoint(
                    {"alembic", "seed", "ensure-ready", "app.main:app"}
                )
            )

    def test_migration_loads_root_env_without_changing_alembic_cwd(self):
        cwd, command = runner.command_plan("v1-migrate", runner.ROOT, "root")[0]
        self.assertEqual(cwd, runner.ROOT / "backendV1")
        self.assertEqual(
            command[-7:],
            [
                "--env-file",
                (runner.ROOT / ".env").as_posix(),
                "alembic",
                "upgrade",
                "head",
                "--tag",
                "qnu-bootstrap",
            ],
        )
        _, backend_command = runner.command_plan("v1-db-check", runner.ROOT, "backend")[
            0
        ]
        self.assertNotIn("--env-file", backend_command)
        self.assertEqual(backend_command[-2:], ["alembic", "current"])

    def test_backend_test_uses_isolation_harness(self):
        _, command = runner.command_plan("v1-test-be", runner.ROOT, "root")[0]
        self.assertEqual(
            Path(command[-1]), runner.ROOT / "backendV1/scripts/run_isolated_tests.py"
        )
        self.assertNotIn("pytest", command)

    def test_missing_env_stops_before_any_process(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(runner, "ROOT", Path(directory)),
            patch.object(runner.subprocess, "run") as run,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as error:
                runner.main(["v1-be", "--env-dir", "backend"])
            self.assertEqual(error.exception.code, 2)
            run.assert_not_called()

    def test_missing_tool_resolves_before_any_service_starts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").touch()
            with (
                patch.object(runner, "ROOT", root),
                patch.object(
                    runner, "resolve_executable", side_effect=["uv", "uv", "uv", None]
                ),
                patch.object(runner.subprocess, "Popen") as popen,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit):
                    runner.main(["dev", "--env-dir", "root"])
                popen.assert_not_called()

    def test_lint_failure_propagates_and_skips_second_command(self):
        with (
            patch.object(runner.shutil, "which", side_effect=lambda name: name),
            patch.object(
                runner.subprocess, "run", return_value=Mock(returncode=7)
            ) as run,
        ):
            self.assertEqual(runner.main(["v1-lint"]), 7)
            self.assertEqual(run.call_count, 1)

    def test_dev_failure_cleans_up_already_started_children(self):
        child = Mock()
        with (
            patch.object(
                runner.subprocess, "Popen", side_effect=[child, OSError("cannot start")]
            ),
            patch.object(runner, "stop_services") as stop,
        ):
            with self.assertRaises(OSError):
                runner.run_services([(runner.ROOT, ["a"]), (runner.ROOT, ["b"])])
            stop.assert_called_once_with([child])

    def test_dev_child_exit_is_error_and_stops_other_children(self):
        children = [Mock(), Mock()]
        children[0].poll.return_value = 0
        with (
            patch.object(runner.subprocess, "Popen", side_effect=children),
            patch.object(runner, "stop_services") as stop,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(
                runner.run_services([(runner.ROOT, ["a"]), (runner.ROOT, ["b"])]), 1
            )
            stop.assert_called_once_with(children)

    def test_ctrl_c_returns_130_and_stops_owned_children(self):
        child = Mock()
        child.poll.side_effect = KeyboardInterrupt
        with (
            patch.object(runner.subprocess, "Popen", return_value=child),
            patch.object(runner, "stop_services") as stop,
        ):
            self.assertEqual(runner.run_services([(runner.ROOT, ["a"])]), 130)
            stop.assert_called_once_with([child])

    def test_backend_env_choice_is_explicit_not_auto_detected(self):
        with (
            patch.dict(os.environ, {"QNU_V1_ENV_DIR": "backend"}),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(runner.main(["v1-dev", "--dry-run"]), 0)
            self.assertEqual(
                Path(json.loads(output.getvalue())[0]["cwd"]),
                runner.ROOT / "backendV1",
            )

    def test_real_process_group_stops_only_owned_child(self):
        options = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **options,
        )
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **options,
        )
        try:
            runner.stop_services([child])
            self.assertIsNotNone(child.poll())
            self.assertIsNone(unrelated.poll())
        finally:
            if child.poll() is None:
                child.kill()
            if unrelated.poll() is None:
                unrelated.kill()
            child.wait()
            unrelated.wait()


if __name__ == "__main__":
    unittest.main()
