import os
import shlex
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
from typing import List, Optional, Tuple

# On Linux we can optionally wrap execution with firejail for isolation.
USE_FIREJAIL = os.getenv("USE_FIREJAIL", "0") == "1"


def _wrap_firejail(cmd: List[str]) -> List[str]:
    if not USE_FIREJAIL:
        return cmd
    # Minimal, no network, private tmp & dev, seccomp enabled
    fj = [
        "firejail",
        "--quiet",
        "--private",
        "--net=none",
        "--private-dev",
        "--rlimit-as=512000000",  # ~512MB address space
        "--rlimit-fsize=1048576",  # max file size 1GB
        "--caps.drop=all",
    ]
    return fj + cmd


def run_in_sandbox(
    argv: List[str],
    *,
    stdin: str = "",
    cwd: Optional[Path] = None,
    timeout_ms: int = 4000,
    env: Optional[dict] = None,
) -> Tuple[str, str, int, int]:
    """Run a command with resource/time limits and optional firejail.
    Returns: (stdout, stderr, exit_code, time_ms)
    """
    cmd = _wrap_firejail(argv)
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            input=stdin.encode(),
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_ms / 1000.0,
        )
        elapsed = int((time.time() - start) * 1000)
        return proc.stdout.decode(errors="replace"), proc.stderr.decode(errors="replace"), proc.returncode, elapsed
    except subprocess.TimeoutExpired as e:
        elapsed = int((time.time() - start) * 1000)
        out = (e.stdout.decode(errors="replace") if e.stdout else "")
        err = (e.stderr.decode(errors="replace") if e.stderr else "")
        return out, (err + "\n[TIMEOUT]"), 124, elapsed