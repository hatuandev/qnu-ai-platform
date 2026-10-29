"""Offline runner regressions: no Docker, application processes, DB or model calls."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import v1_e2e_session as runner


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.manifest = {"cleaned": False}

    def test_stale_running_flag_allows_cleanup_only_after_runtime_checks(self):
        runner.save(self.directory / "server.json", {"running": True})
        events = []
        with (
            patch.object(
                runner,
                "require_stopped_services",
                side_effect=lambda _: events.append("checked"),
            ),
            patch.object(
                runner, "compose", side_effect=lambda *args: events.append("down")
            ),
        ):
            runner.cleanup(self.directory, self.manifest)
        self.assertEqual(events, ["checked", "down"])
        self.assertFalse(runner.read(self.directory / "server.json")["running"])
        self.assertTrue(runner.read(self.directory / "manifest.json")["cleaned"])

    def test_connected_worker_prevents_cleanup(self):
        with (
            patch.object(
                runner,
                "require_stopped_services",
                side_effect=RuntimeError("worker alive"),
            ),
            patch.object(runner, "compose") as compose,
            self.assertRaisesRegex(RuntimeError, "worker alive"),
        ):
            runner.cleanup(self.directory, self.manifest)
        compose.assert_not_called()
        self.assertFalse(self.manifest["cleaned"])

    def test_stage_lock_prevents_cleanup(self):
        (self.directory / "stage.lock").touch()
        with (
            patch.object(runner, "compose") as compose,
            self.assertRaisesRegex(RuntimeError, "stage"),
        ):
            runner.cleanup(self.directory, self.manifest)
        compose.assert_not_called()

    def test_active_serve_lease_blocks_cleanup(self):
        with (
            runner.server_lease(self.directory),
            patch.object(runner, "compose") as compose,
            self.assertRaisesRegex(RuntimeError, "Serve"),
        ):
            runner.cleanup(self.directory, self.manifest)
        compose.assert_not_called()

    def test_preflight_failure_clears_running_state_and_releases_lease(self):
        with (
            patch.object(runner, "require_stopped_services"),
            patch.object(runner, "_serve", side_effect=RuntimeError("bad DOCX")),
            self.assertRaisesRegex(RuntimeError, "DOCX"),
        ):
            runner.serve(self.directory, self.manifest)
        self.assertFalse(runner.read(self.directory / "server.json")["running"])
        with runner.server_lease(self.directory):
            pass

    def test_stopped_services_still_checks_worker_connections(self):
        socket = Mock()
        socket.__enter__ = Mock(return_value=socket)
        socket.__exit__ = Mock(return_value=False)
        socket.connect_ex.return_value = 1
        with (
            patch.object(runner.socket, "socket", return_value=socket),
            patch.object(runner, "infrastructure_clients", return_value=[12345]),
            self.assertRaisesRegex(RuntimeError, "12345"),
        ):
            runner.require_stopped_services(
                {"ports": {"api": 1, "frontend": 2, "mock": 3}}
            )


if __name__ == "__main__":
    unittest.main()
