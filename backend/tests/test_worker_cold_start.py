import os
import subprocess
import sys


def test_worker_settings_imports_in_a_fresh_process_without_importing_api_first():
    result = subprocess.run([sys.executable, '-c', 'from app.workers.arq_worker import WorkerSettings; assert WorkerSettings.functions'],
        env=os.environ.copy(), capture_output=True, text=True, timeout=40, check=False)
    assert result.returncode == 0, result.stderr[-5000:]
