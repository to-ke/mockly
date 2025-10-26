import json
from pathlib import Path
import random
import uuid

import yaml
from fastapi import APIRouter, HTTPException

from ..models import QuestionRequest, QuestionPayload

router = APIRouter(prefix="/api", tags=["questions"])

# questions.yaml lives at the project root (../questions.yaml) so resolve explicitly.
QUESTIONS_FILE = Path(__file__).resolve().parent.parent.parent / "questions.yaml"


def _load_index_by_difficulty() -> dict[str, list[dict]]:
    """
    Load questions.yaml and build an index: difficulty -> list[problem dicts].
    Expected YAML shape (simplified):

    difficulties:
      - difficulty: <easy|medium|hard>
        problems:
          - title: "Two Sum"
            statement: "..."
            input_format: "..."
            output_format: "..."
            examples: [...]
            hints: [...]
    """
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    index: dict[str, list[dict]] = {}
    for entry in data.get("difficulties", []):
        diff = str(entry.get("difficulty", "")).strip().lower()
        problems = entry.get("problems") or []
        if diff:
            index[diff] = problems
    return index


# Load once; in prod you could add a reload flag or watchdog if the YAML changes.
_INDEX_BY_DIFF = _load_index_by_difficulty()


def _format_examples(problem: dict) -> str:
    examples = problem.get("examples") or []
    if not examples:
        return ""

    lines: list[str] = ["Examples:"]
    for idx, example in enumerate(examples, start=1):
        name = example.get("name") or f"Example {idx}"
        lines.append(f"- {name}:")
        if example.get("input") is not None:
            lines.append(f"    Input: {json.dumps(example['input'])}")
        if example.get("output") is not None:
            lines.append(f"    Output: {json.dumps(example['output'])}")
        if example.get("explanation"):
            lines.append(f"    Explanation: {example['explanation']}")
    return "\n".join(lines)


def _get_starter_code_for_language(problem: dict, language: str) -> str:
    """Get starter code for the specified language, falling back to default if not available."""
    language_map = {
        "javascript": "starter_code_javascript",
        "java": "starter_code_java", 
        "cpp": "starter_code_cpp",
        "typescript": "starter_code_typescript",
        "go": "starter_code_go",
        "c": "starter_code_c",
        "csharp": "starter_code_csharp",
        "kotlin": "starter_code_kotlin",
        "ruby": "starter_code_ruby",
        "perl": "starter_code_perl",
    }
    
    # Get the appropriate starter code field for the language
    starter_code_field = language_map.get(language, "starter_code")  # default to python
    return (problem.get(starter_code_field) or "").rstrip()


@router.post("/questions", response_model=QuestionPayload)
def fetch_question(req: QuestionRequest) -> QuestionPayload:
    # difficulty is case-insensitive in the YAML index
    bucket = _INDEX_BY_DIFF.get(req.difficulty.lower())
    if not bucket:
        raise HTTPException(status_code=404, detail=f"No questions for {req.difficulty}")

    item = random.choice(bucket)

    # Map YAML fields -> frontend payload
    # YAML uses 'statement' as the main problem description. Attach rendered examples.
    prompt = (item.get("statement", "") or "").strip()
    examples_blob = _format_examples(item)
    if examples_blob:
        prompt = f"{prompt}\n\n{examples_blob}"

    # Get starter code for the requested language
    starter_code = _get_starter_code_for_language(item, req.language)
    
    return QuestionPayload(
        id=f"{req.difficulty}-{uuid.uuid4().hex[:8]}",
        difficulty=req.difficulty,
        prompt=prompt,
        starter_code=starter_code or None,
        language=req.language,
        answers=None,
    )
