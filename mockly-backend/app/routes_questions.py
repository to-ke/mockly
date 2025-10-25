from fastapi import APIRouter, HTTPException
from .models import QuestionRequest, QuestionPayload
from pathlib import Path
import yaml
import uuid
import random

router = APIRouter(prefix="/api", tags=["questions"])

QUESTIONS_FILE = Path(__file__).with_name("questions.yaml")


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


@router.post("/questions", response_model=QuestionPayload)
def fetch_question(req: QuestionRequest) -> QuestionPayload:
    # difficulty is case-insensitive in the YAML index
    bucket = _INDEX_BY_DIFF.get(req.difficulty.lower())
    if not bucket:
        raise HTTPException(status_code=404, detail=f"No questions for {req.difficulty}")

    item = random.choice(bucket)

    # Map YAML fields -> frontend payload
    # YAML uses 'statement' as the main problem description.
    prompt = item.get("statement", "") or ""

    return QuestionPayload(
        id=f"{req.difficulty}-{uuid.uuid4().hex[:8]}",
        difficulty=req.difficulty,
        prompt=prompt,
        starter_code=None,
        answers=None,
    )
