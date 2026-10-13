"""Portable launcher, independent of asyncio's Windows subprocess support."""

import os
import subprocess
import sys

from app.modules.backups.processes import process_options


def spawn_runner(backup_id: str, password: str) -> subprocess.Popen[bytes]:
    """Called off the request loop; no shell, secret argv, env secret or visible window."""
    process = subprocess.Popen(
        [sys.executable, "-m", "app.modules.backups.runner", backup_id],
        cwd=os.getcwd(),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **process_options(),
    )
    try:
        # Max 256 characters: bounded pipe write. Password is consumed once and
        # EOF closes stdin; runner decodes explicitly as UTF-8 on every OS.
        process.stdin.write((password + "\n").encode("utf-8"))
        process.stdin.flush()
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        raise
    finally:
        process.stdin.close()
    return process
