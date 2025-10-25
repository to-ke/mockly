from fastapi import APIRouter, HTTPException
from .models import ExecuteRequest, ExecuteResponse
from .sandbox import run_in_sandbox
import tempfile
from pathlib import Path

router = APIRouter(prefix="/api", tags=["execute"]) 


def _lang_to_commands(language: str, workdir: Path, filename_hint: str | None) -> tuple[list[str], list[str] | None, Path]:
    """Return (run_cmd, compile_cmd_or_None, source_path)."""
    if language == "python":
        src = workdir / (filename_hint or "Main.py")
        run = ["python", str(src)]
        return run, None, src
    if language == "javascript":
        src = workdir / (filename_hint or "main.js")
        run = ["node", str(src)]
        return run, None, src
    if language == "typescript":
        # transpile inline using ts-node/register if available; otherwise tsc
        src = workdir / (filename_hint or "main.ts")
        # prefer ts-node
        run = ["node", "-e", f"require('ts-node/register');require('{src.as_posix()}')"]
        return run, None, src
    if language == "java":
        src = workdir / (filename_hint or "Main.java")
        compile_cmd = ["javac", str(src)]
        run_cmd = ["java", "-cp", str(workdir), src.stem]
        return run_cmd, compile_cmd, src
    if language == "cpp":
        src = workdir / (filename_hint or "main.cpp")
        exe = workdir / "a.out"
        compile_cmd = ["g++", str(src), "-O2", "-std=c++17", "-o", str(exe)]
        run_cmd = [str(exe)]
        return run_cmd, compile_cmd, src
    raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")


@router.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest) -> ExecuteResponse:
    # Empty source check mirrors frontend behavior
    if not req.source or not req.source.strip():
        raise HTTPException(status_code=400, detail="No source provided")

    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        run_cmd, compile_cmd, src_path = _lang_to_commands(req.language, workdir, req.filename)
        src_path.write_text(req.source, encoding="utf-8")

        # Compile if needed
        if compile_cmd:
            _o, err, code, _t = run_in_sandbox(compile_cmd, cwd=workdir, timeout_ms=min(req.time_limit_ms, 8000))
            if code != 0:
                return ExecuteResponse(stdout="", stderr=err, exitCode=code)

        # Run
        out, err, code, t = run_in_sandbox(run_cmd, stdin=req.stdin or "", cwd=workdir, timeout_ms=req.time_limit_ms)
        return ExecuteResponse(stdout=out, stderr=err, exitCode=code, timeMs=t)