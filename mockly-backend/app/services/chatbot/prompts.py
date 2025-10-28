"""Prompt helpers and question loader.

This module contains `build_system_prompt_from_question` and a small
helper to load a question by difficulty from a `questions.yaml` file
if present. The implementation mirrors the behavior in
`workflow/api.py` but is colocated here for the chatbot package.
"""
from pathlib import Path
from typing import Any
import re

try:
    import yaml as _yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _yaml = None


def _format_examples(examples) -> str:
    try:
        if not examples:
            return ""
        lines = []
        for ex in examples:
            if isinstance(ex, dict):
                name = ex.get("name") or ex.get("title") or "example"
                inp = ex.get("input")
                out = ex.get("output")
                expl = ex.get("explanation")
                seg = f"- {name}:\n  input: {inp}\n  output: {out}"
                if expl:
                    seg += f"\n  note: {expl}"
                lines.append(seg)
            else:
                lines.append(f"- {ex}")
        return "\n".join(lines)
    except Exception:
        return ""


def _find_questions_yaml() -> Path | None:
    # We expect this file under the project root (mockly-backend)
    base = Path(__file__).resolve().parents[3]  # mockly-backend
    for cand in [base / "app" / "questions.yaml", base / "questions.yaml"]:
        if cand.exists():
            return cand
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
    diffs = data.get("difficulties") or []
    target = str(difficulty).strip().lower()
    for entry in diffs:
        if str(entry.get("difficulty", "")).strip().lower() == target:
            problems = entry.get("problems") or []
            if problems:
                q = dict(problems[0])
                q.setdefault("difficulty", difficulty)
                return q
            break
    return None


def build_system_prompt_from_question(question: dict | None) -> str:
    """Construct the interviewer system prompt from a question dict.

    The prompt format intentionally mirrors the long template in
    `workflow/api.py` so existing endpoints can reuse it.
    """
    if not isinstance(question, dict):
        question = {}

    title = (question.get("title") or "").strip()
    difficulty = (question.get("difficulty") or "").strip()
    statement = (question.get("statement") or question.get("prompt") or "").strip()
    input_fmt = (question.get("input_format") or "").strip()
    output_fmt = (question.get("output_format") or "").strip()
    examples = _format_examples(question.get("examples"))
    hints = question.get("hints") or []
    hints_list: list[str] = []
    if isinstance(hints, list):
        hints_list = [str(h).strip() for h in hints if str(h).strip()]
    else:
        if str(hints).strip():
            hints_list = [str(hints).strip()]

    limited_hints = hints_list[:2]
    limited_hints_text = "\n".join(f"- {h}" for h in limited_hints)

    qd_lines: list[str] = []
    if title or difficulty:
        head = []
        if title:
            head.append(f"Title: {title}")
        if difficulty:
            head.append(f"Difficulty: {difficulty}")
        qd_lines.append(" ".join(head))
        qd_lines.append("")
    if statement:
        qd_lines.append("Problem Statement:")
        qd_lines.append(statement)
        qd_lines.append("")
    if input_fmt:
        qd_lines.append("Input Format:")
        qd_lines.append(input_fmt)
        qd_lines.append("")
    if output_fmt:
        qd_lines.append("Output Format:")
        qd_lines.append(output_fmt)
        qd_lines.append("")
    if examples:
        qd_lines.append("Examples:")
        qd_lines.append(examples)
        qd_lines.append("")
    if limited_hints_text:
        qd_lines.append("Hints (use at most two; ordered):")
        qd_lines.append(limited_hints_text)
        qd_lines.append("")

    question_details = "\n".join([ln for ln in qd_lines if ln is not None])

    parts = [
        "You will be acting as a technical interviewer conducting a coding interview with a candidate. "
        "You will present them with a LeetCode-style algorithmic problem and evaluate their performance.",
        "",
        "Here are the question details you should use:",
        "<question_details>",
        question_details,
        "</question_details>",
        "",
        "When I write BEGIN INTERVIEW, you will start the technical interview. "
        "All further input will be from the candidate attempting to solve the problem.",
        "",
        "Here are the important rules for conducting the interview:",
        "",
        "**Voice Output Rules (Important):**",
        "- Speak naturally and conversationally; avoid robotic or literal reading.",
        "- Do NOT vocalize formatting symbols like **, __, #, ##, <...>, </...>, backticks, or code fences.",
        "- Do not say phrases like 'star star' or 'pound pound'; omit formatting markers entirely.",
        "- When presenting structure, use plain sentences (e.g., 'Code Cleanliness score is 4 out of 5').",
        "- Do not read XML-like tags (e.g., <evaluation>) aloud; treat them as meta and exclude them from speech.",
        "",
        "**Presenting the Problem:**",
        "- ONLY present the full problem when the user's message is exactly 'BEGIN INTERVIEW'",
        "- Present the coding question in a language-agnostic way since the candidate can choose any programming language",
        "- Clearly state the problem, provide examples, and specify any constraints",
        "- Do not mention specific language syntax or data structures that are language-specific",
        "- Do not ask what programming language they want to use; stay language-agnostic unless they volunteer a preference",
        "",
        "**Responding to User Questions:**",
        "- If the user asks a question or makes a comment, respond DIRECTLY to it without re-presenting the problem",
        "- Do NOT reintroduce or restate the problem statement unless explicitly asked",
        "- Focus on answering their specific question or responding to their input",
        "- Keep responses concise and focused on what they asked",
        "- Be direct and professional; avoid asking follow-up questions like 'Does that help?' or 'Do you have any questions?'",
        "- Let the candidate drive the conversation; don't prompt them or check in unnecessarily",
        "- Answer their question clearly and then STOP; don't offer additional help unless asked",
        "",
        "**Giving Hints:**",
        "- You have exactly TWO hints available from the question details",
        "- Only provide a hint if the candidate is clearly stuck or explicitly asks for help",
        "- Give hints one at a time, not both at once",
        "- Keep track of how many hints you've used",
        "",
        "**During the Interview:**",
        "- Allow the candidate to think through the problem and ask clarifying questions",
        "- Be supportive but don't give away the solution",
        "- Be professional and direct; avoid being overly accommodating or catering",
        "- Do not ask if they need help, have questions, or understand; wait for them to ask",
        "- If they finish or get significantly stuck, move to the evaluation phase",
        "",
        "**Evaluation Criteria:**",
        "After the coding session, you will evaluate the candidate on three categories, each rated 1-5:",
        "",
        "1. **Code Cleanliness** - Consider readability, proper variable naming, code organization, and adherence to good coding practices",
        "2. **Communication** - Evaluate how well they explained their approach, asked clarifying questions, and walked through their solution",
        "3. **Efficiency** - Assess the time and space complexity of their solution and whether they considered optimization",
        "",
        "**Output Format:**",
        "When providing your evaluation, structure it as follows:",
        "",
        "For each category, first provide detailed feedback on what the candidate did well and areas for improvement, then give the numerical score. Use this format:",
        "",
        "<evaluation>",
        "**Code Cleanliness:**",
        "[Detailed feedback on code quality, naming conventions, structure, etc.]",
        "Score: [1-5]",
        "",
        "**Communication:**",
        "[Detailed feedback on how well they explained their thinking, asked questions, etc.]",
        "Score: [1-5]",
        "",
        "**Efficiency:**",
        "[Detailed feedback on algorithmic complexity, optimization considerations, etc.]",
        "Score: [1-5]",
        "",
        "**Overall Comments:**",
        "[Any additional feedback or suggestions for improvement]",
        "</evaluation>",
        "",
        "Remember to be constructive in your feedback and provide specific examples of what they could improve.",
        "",
        "BEGIN INTERVIEW",
    ]

    return "\n".join(part for part in parts if part is not None)


__all__ = [
    "build_system_prompt_from_question",
    "load_question_by_difficulty",
]
