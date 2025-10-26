"""
Utilities for loading interview questions from questions.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml as _yaml  # type: ignore
except Exception:  # pragma: no cover
    _yaml = None


def _project_root() -> Path:
    # file -> workflow -> services -> app -> project-root
    return Path(__file__).resolve().parents[3]


def _find_questions_yaml() -> Path | None:
    base = _project_root()
    for candidate in [base / "app" / "questions.yaml", base / "questions.yaml"]:
        if candidate.exists():
            return candidate
    return None


def load_question_by_difficulty(difficulty: str) -> dict | None:
    if not difficulty:
        return None
    if _yaml is None:
        raise RuntimeError("PyYAML not installed; cannot load questions.yaml. Add PyYAML to requirements and install.")
    path = _find_questions_yaml()
    if not path:
        raise FileNotFoundError("questions.yaml not found under app/ or project root.")

    data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    difficulties = data.get("difficulties") or []
    target = str(difficulty).strip().lower()
    for entry in difficulties:
        if str(entry.get("difficulty", "")).strip().lower() == target:
            problems = entry.get("problems") or []
            if problems:
                question = dict(problems[0])
                question.setdefault("difficulty", difficulty)
                return question
            break
    return None


__all__ = ["load_question_by_difficulty"]
