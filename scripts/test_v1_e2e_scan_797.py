"""OCR stage is isolated and cannot inherit an image experiment from the shell."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import v1_e2e_session as runner


class ScanStageTests(unittest.TestCase):
    def test_separate_prerequisites_history_and_explicit_dpi(self):
        for dpi in (None, 176):
            with self.subTest(dpi=dpi), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                prior = {"status": "FAIL", "report": "original-53-cases"}
                runner.save(
                    directory / "checkpoint.json",
                    {
                        "results": {
                            **{
                                s: {"status": "PASS"}
                                for s in (
                                    "provider-setup",
                                    "model-discovery",
                                    "model-ocr",
                                    "navigation",
                                )
                            },
                            "admissions-chat": prior,
                        }
                    },
                )
                runner.save(
                    directory / "server.json",
                    {
                        "running": True,
                        "backend_source_sha256": "revision",
                    },
                )
                captured = {}

                def execute(_args, *, cwd, env, check, captured=captured):
                    captured.update(env)
                    runner.save(
                        Path(env["E2E_OUTPUT"]) / "results.json",
                        {
                            "stats": {"expected": 1},
                        },
                    )
                    return SimpleNamespace(returncode=0)

                with (
                    patch.object(
                        runner, "environment", return_value={"E2E_SCAN_OCR_DPI": "300"}
                    ),
                    patch.object(
                        runner, "backend_source_hash", return_value="revision"
                    ),
                    patch.object(runner.subprocess, "run", side_effect=execute),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    result = runner.run_stage(
                        directory,
                        {
                            "mode": "live",
                            "ports": {"frontend": 64625},
                        },
                        "admissions-scan-ocr",
                        False,
                        ocr_dpi=dpi,
                    )
                self.assertEqual(result, 0)
                self.assertEqual(
                    captured["E2E_SCAN_OCR_DPI"], "" if dpi is None else "176"
                )
                self.assertEqual(
                    runner.read(directory / "checkpoint.json")["results"][
                        "admissions-chat"
                    ],
                    prior,
                )

    def test_missing_ocr_diagnostic_blocks_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            runner.save(directory / "checkpoint.json", {"results": {}})
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = runner.run_stage(
                    directory, {"mode": "live"}, "admissions-scan-ocr", False
                )
            self.assertEqual(code, 2)
            self.assertIn("model-ocr", out.getvalue())


if __name__ == "__main__":
    unittest.main()
