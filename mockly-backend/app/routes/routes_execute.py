import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter

from ..models import ExecuteRequest, ExecuteResponse


router = APIRouter(prefix="/api", tags=["execute"])


EXEC_ROOT = Path("/app/.runner")
EXEC_ROOT.mkdir(parents=True, exist_ok=True)


# Simple "write file and run interpreter" commands.
TS_COMPILER_OPTIONS = '{"module":"commonjs","moduleResolution":"node"}'


INTERPRETED_COMMANDS: Dict[str, Dict[str, List[str]]] = {
    "python": {"extension": ".py", "cmd": ["python3", "{file}"]},
    "javascript": {"extension": ".js", "cmd": ["node", "{file}"]},
    "typescript": {
        "extension": ".ts",
        "cmd": [
            "ts-node",
            "--transpile-only",
            "--compiler-options",
            TS_COMPILER_OPTIONS,
            "{file}",
        ],
    },
}

DEFAULT_TIMEOUT_SECONDS = 5.0


def _run_process(
    cmd: List[str],
    stdin_bytes: Optional[bytes],
    timeout: float,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        input=stdin_bytes,
        capture_output=True,
        timeout=timeout,
    )


@router.post("/execute", response_model=ExecuteResponse)
def execute_code(payload: ExecuteRequest) -> ExecuteResponse:
    timeout = (
        max(payload.timeoutMs, 1) / 1000 if payload.timeoutMs else DEFAULT_TIMEOUT_SECONDS
    )

    with tempfile.TemporaryDirectory(dir=EXEC_ROOT) as tmp_dir:
        stdin_bytes = payload.stdin.encode() if payload.stdin else None
        started = time.perf_counter()

        config = INTERPRETED_COMMANDS.get(payload.language)
        if config:
            return _run_interpreted(config, payload, stdin_bytes, timeout, tmp_dir, started)

        if payload.language == "cpp":
            return _run_cpp(payload, stdin_bytes, timeout, tmp_dir, started)

        if payload.language == "java":
            return _run_java(payload, stdin_bytes, timeout, tmp_dir, started)

        return ExecuteResponse(
            stdout="",
            stderr=f"Language '{payload.language}' is not supported.",
            exitCode=1,
        )


def _run_interpreted(config, payload, stdin_bytes, timeout, tmp_dir, started):
    source_path = Path(tmp_dir) / f"Main{config['extension']}"
    source_path.write_text(payload.source)
    cmd = [
        arg.format(file=str(source_path)) if "{file}" in arg else arg
        for arg in config["cmd"]
    ]
    try:
        proc = _run_process(cmd, stdin_bytes, timeout)
    except FileNotFoundError:
        return ExecuteResponse(
            stdout="",
            stderr=f"Runner for '{payload.language}' is not available on the server.",
            exitCode=1,
        )
    except subprocess.TimeoutExpired as exc:
        return _timeout_response(exc, timeout)

    duration_ms = int((time.perf_counter() - started) * 1000)
    return ExecuteResponse(
        stdout=proc.stdout.decode("utf-8", errors="replace"),
        stderr=proc.stderr.decode("utf-8", errors="replace"),
        exitCode=proc.returncode,
        timeMs=duration_ms,
    )


def _run_cpp(payload, stdin_bytes, timeout, tmp_dir, started):
    source_path = Path(tmp_dir) / "main.cpp"
    exe_path = Path(tmp_dir) / "main.bin"
    source_path.write_text(payload.source)

    compile_cmd = [
        "g++",
        str(source_path),
        "-std=c++17",
        "-O2",
        "-pipe",
        "-o",
        str(exe_path),
    ]
    try:
        compile_proc = _run_process(compile_cmd, None, timeout)
    except FileNotFoundError:
        return ExecuteResponse(
            stdout="",
            stderr="C++ compiler is not available on the server.",
            exitCode=1,
        )
    if compile_proc.returncode != 0:
        return ExecuteResponse(
            stdout=compile_proc.stdout.decode("utf-8", errors="replace"),
            stderr=compile_proc.stderr.decode("utf-8", errors="replace"),
            exitCode=compile_proc.returncode,
        )

    # Ensure the compiled binary is executable even if the toolchain omits +x.
    try:
        exe_path.chmod(0o755)
    except FileNotFoundError:
        return ExecuteResponse(
            stdout="",
            stderr="C++ runner failed to produce an executable binary.",
            exitCode=1,
        )

    try:
        run_proc = _run_process([str(exe_path)], stdin_bytes, timeout)
    except subprocess.TimeoutExpired as exc:
        return _timeout_response(exc, timeout)
    except PermissionError:
        return ExecuteResponse(
            stdout="",
            stderr="C++ binary could not be executed (permission denied).",
            exitCode=1,
        )
    except FileNotFoundError:
        return ExecuteResponse(
            stdout="",
            stderr="C++ runner is not available on the server.",
            exitCode=1,
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    return ExecuteResponse(
        stdout=run_proc.stdout.decode("utf-8", errors="replace"),
        stderr=run_proc.stderr.decode("utf-8", errors="replace"),
        exitCode=run_proc.returncode,
        timeMs=duration_ms,
    )


def _run_java(payload, stdin_bytes, timeout, tmp_dir, started):
    source_path = Path(tmp_dir) / "Main.java"
    source_path.write_text(payload.source)

    compile_cmd = ["javac", str(source_path)]
    try:
        compile_proc = _run_process(compile_cmd, None, timeout)
    except FileNotFoundError:
        return ExecuteResponse(
            stdout="",
            stderr="Java compiler is not available on the server.",
            exitCode=1,
        )
    if compile_proc.returncode != 0:
        return ExecuteResponse(
            stdout=compile_proc.stdout.decode("utf-8", errors="replace"),
            stderr=compile_proc.stderr.decode("utf-8", errors="replace"),
            exitCode=compile_proc.returncode,
        )

    run_cmd = ["java", "-cp", str(tmp_dir), "Main"]
    try:
        run_proc = _run_process(run_cmd, stdin_bytes, timeout)
    except FileNotFoundError:
        return ExecuteResponse(
            stdout="",
            stderr="Java runtime is not available on the server.",
            exitCode=1,
        )
    except subprocess.TimeoutExpired as exc:
        return _timeout_response(exc, timeout)

    duration_ms = int((time.perf_counter() - started) * 1000)
    return ExecuteResponse(
        stdout=run_proc.stdout.decode("utf-8", errors="replace"),
        stderr=run_proc.stderr.decode("utf-8", errors="replace"),
        exitCode=run_proc.returncode,
        timeMs=duration_ms,
    )


def _timeout_response(exc: subprocess.TimeoutExpired, timeout: float) -> ExecuteResponse:
    stdout = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
    stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
    if stderr:
        stderr = f"{stderr}\nExecution timed out."
    else:
        stderr = "Execution timed out."
    return ExecuteResponse(
        stdout=stdout,
        stderr=stderr,
        exitCode=124,
        timeMs=int(timeout * 1000),
    )
