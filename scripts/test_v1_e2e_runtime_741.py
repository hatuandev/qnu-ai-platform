"""Runner freshness regressions; no infrastructure or model calls."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import v1_e2e_session as runner


class RuntimeFreshnessTests(unittest.TestCase):
    def test_unverified_or_changed_server_blocks_before_stage_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            runner.save(directory / "checkpoint.json", {"results": {}})
            for server in (
                {"running": True},
                {"running": True, "backend_source_sha256": "old"},
            ):
                with self.subTest(server=server):
                    runner.save(directory / "server.json", server)
                    with (
                        patch.object(runner, "backend_source_hash", return_value="new"),
                        patch.object(runner, "environment") as environment,
                        patch.object(runner.subprocess, "run") as launch,
                        contextlib.redirect_stdout(io.StringIO()) as output,
                    ):
                        result = runner.run_stage(
                            directory, {"mode": "workflow"}, "navigation", False
                        )
                    self.assertEqual(result, 2)
                    self.assertIn("Ctrl+C", output.getvalue())
                    self.assertIn("Không cleanup/init", output.getvalue())
                    environment.assert_not_called()
                    launch.assert_not_called()

    def test_source_content_change_is_detected_but_timestamp_alone_is_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            backend = Path(temporary)
            source = backend / "qnu" / "example.py"
            source.parent.mkdir()
            source.write_text("VERSION = 2\n", encoding="utf-8")
            with patch.object(runner, "BE", backend):
                original = runner.backend_source_hash()
                source.touch()
                self.assertEqual(runner.backend_source_hash(), original)
                source.write_text("VERSION = 3\n", encoding="utf-8")
                self.assertNotEqual(runner.backend_source_hash(), original)


if __name__ == "__main__":
    unittest.main()
