from fastapi import APIRouter
from ..models import FeedbackReport

router = APIRouter(prefix="/api", tags=["feedback"]) 

@router.get("/feedback", response_model=FeedbackReport)
def feedback() -> FeedbackReport:
    # Static example; in real life this would be computed per session
    return FeedbackReport(
        communication=4,
        codeCleanliness=5,
        codeEfficiency=4,
        comments=(
            "Strong communication throughout the session with clear explanations. "
            "Code was well structured and easy to follow. Consider optimizing your "
            "solution to reduce time complexity in future iterations."
        ),
    )