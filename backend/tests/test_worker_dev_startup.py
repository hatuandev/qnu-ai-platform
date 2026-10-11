"""Development runners must start the queue consumer, not only API/FE."""

from pathlib import Path

import pytest

from app.workers.arq_worker import WorkerSettings

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("runner", ["make.ps1", "make.bat", "make", "Makefile"])
def test_dev_and_worker_commands_use_shared_launcher(runner):
    source = (ROOT / runner).read_text(encoding="utf-8")
    assert "start-worker.ps1" in source
    assert "worker" in source


def test_background_worker_has_logs_and_hidden_window():
    source = (ROOT / "scripts/start-worker.ps1").read_text(encoding="utf-8")
    assert "-WindowStyle Hidden" in source
    assert "-RedirectStandardError" in source
    assert "-RedirectStandardOutput" in source
    assert "app.workers.arq_worker.WorkerSettings" in source


def test_worker_health_does_not_remain_stale_for_an_hour():
    assert WorkerSettings.health_check_interval <= 30
