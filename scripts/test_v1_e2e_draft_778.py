"""Draft-only prerequisites bypass review only with an explicit operator choice."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import v1_e2e_session as runner


class DraftStageTests(unittest.TestCase):
    def blocked(self, stage, passed, skip_review=False):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            runner.save(
                directory / "checkpoint.json",
                {"results": {name: {"status": "PASS"} for name in passed}},
            )
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = runner.run_stage(
                    directory, {"mode": "live"}, stage, False, skip_review=skip_review
                )
            self.assertEqual(code, 2)
            return output.getvalue()

    def test_draft_requires_extraction(self):
        output = self.blocked("admissions-draft", runner.MODEL_STAGES + ("navigation",))
        self.assertIn("admissions-extraction", output)

    def test_normal_compilation_does_not_require_optional_draft_stage(self):
        prerequisites = runner.MODEL_STAGES + (
            "navigation",
            "admissions-upload",
            "admissions-extraction",
        )
        for stage in ("admissions-draft", "admissions-compilation"):
            with self.subTest(stage=stage):
                self.assertIn("chạy serve", self.blocked(stage, prerequisites))

    def test_draft_pass_never_unlocks_publication(self):
        prerequisites = runner.MODEL_STAGES + (
            "navigation",
            "admissions-upload",
            "admissions-extraction",
            "admissions-draft",
        )
        self.assertIn(
            "admissions-compilation",
            self.blocked("admissions-publication", prerequisites),
        )
        self.assertIn(
            "chạy serve",
            self.blocked("admissions-publication", prerequisites, skip_review=True),
        )

    def test_inherited_skip_flag_does_not_override_cli_choice(self):
        for skip_review in (False, True):
            with (
                self.subTest(skip_review=skip_review),
                tempfile.TemporaryDirectory() as temporary,
            ):
                directory = Path(temporary)
                runner.save(
                    directory / "checkpoint.json",
                    {
                        "results": {
                            name: {"status": "PASS"}
                            for name in (
                                *runner.MODEL_STAGES,
                                "navigation",
                                *runner.ADMISSIONS_STAGES[:-1],
                            )
                        }
                    },
                )
                runner.save(
                    directory / "server.json",
                    {"running": True, "backend_source_sha256": "revision"},
                )
                captured = {}

                def run(_args, *, cwd, env, check, captured=captured):
                    captured.update(env)
                    runner.save(
                        Path(env["E2E_OUTPUT"]) / "results.json",
                        {"stats": {"expected": 1}},
                    )
                    return SimpleNamespace(returncode=0)

                with (
                    patch.object(
                        runner, "environment", return_value={"E2E_SKIP_REVIEW": "1"}
                    ),
                    patch.object(
                        runner, "backend_source_hash", return_value="revision"
                    ),
                    patch.object(runner.subprocess, "run", side_effect=run),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    code = runner.run_stage(
                        directory,
                        {"mode": "live", "ports": {"frontend": 64625}},
                        "admissions-publication",
                        False,
                        skip_review=skip_review,
                    )
                self.assertEqual(code, 0)
                self.assertEqual(
                    captured["E2E_SKIP_REVIEW"], "1" if skip_review else "0"
                )
                saved = runner.read(directory / "checkpoint.json")["results"][
                    "admissions-publication"
                ]
                self.assertEqual(
                    saved.get("review_mode"), "skipped" if skip_review else None
                )


if __name__ == "__main__":
    unittest.main()
