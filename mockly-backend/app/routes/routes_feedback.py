from fastapi import APIRouter, Body, HTTPException
from ..models import FeedbackReport
from ..services.workflow.prompts import build_code_evaluation_prompt
from ..services.workflow.evaluation import parse_evaluation_scores
from ..services.workflow.clients import anthropic_client
from ..services.workflow.config import ANTHROPIC_MODEL
from ..services.workflow.questions import load_question_by_difficulty

router = APIRouter(prefix="/api", tags=["feedback"]) 

@router.post("/feedback", response_model=FeedbackReport)
def feedback(payload: dict = Body(...)) -> FeedbackReport:
    """
    Evaluate code submission using Claude AI.
    
    Expected payload:
    - code: The candidate's code (required)
    - language: Programming language (required)
    - question: Optional question context (title, difficulty, statement, or just difficulty)
    """
    code = payload.get("code", "").strip()
    language = payload.get("language", "python").strip()
    question = payload.get("question")
    
    # If question only has difficulty, load full question details
    if question and isinstance(question, dict):
        difficulty = question.get("difficulty")
        if difficulty and not question.get("statement") and not question.get("prompt"):
            try:
                full_question = load_question_by_difficulty(difficulty)
                if full_question:
                    question = full_question
            except Exception:
                pass  # Continue with partial question info
    
    if not code:
        raise HTTPException(400, "Field 'code' is required")
    
    # Build the evaluation prompt with code
    evaluation_prompt = build_code_evaluation_prompt(code, language, question)
    
    try:
        # Call Claude to evaluate the code
        message = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            messages=[{"role": "user", "content": evaluation_prompt}],
            max_tokens=4096,
        )
        
        # Extract the text response
        full_text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        
        # Parse the evaluation scores
        parsed = parse_evaluation_scores(full_text)
        
        # Extract scores with defaults
        code_cleanliness = parsed.get("code_cleanliness") or 3
        communication = parsed.get("communication") or 3
        efficiency = parsed.get("efficiency") or 3
        
        # Format the response for better display
        import re
        
        # Extract content between <evaluation> tags if present
        eval_match = re.search(r'<evaluation>(.*?)</evaluation>', full_text, re.DOTALL | re.IGNORECASE)
        eval_text = eval_match.group(1).strip() if eval_match else full_text
        
        # Extract each section's feedback (without the scores)
        def extract_section_feedback(text: str, section_name: str) -> str:
            """Extract feedback for a specific section, excluding the score line."""
            pattern = rf'\*\*{section_name}:\*\*\s*(.*?)(?=\*\*[A-Z]|\Z)'
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                feedback = match.group(1).strip()
                # Remove the "Score: X" line
                feedback = re.sub(r'\s*Score:\s*[1-5]\s*', '', feedback, flags=re.IGNORECASE)
                return feedback.strip()
            return ""
        
        # Extract feedback for each category
        cleanliness_feedback = extract_section_feedback(eval_text, "Code Cleanliness")
        communication_feedback = extract_section_feedback(eval_text, "Communication")
        efficiency_feedback = extract_section_feedback(eval_text, "Efficiency")
        overall_feedback = extract_section_feedback(eval_text, "Overall Comments")
        
        # Format as markdown with clear sections
        comments_parts = []
        
        if cleanliness_feedback:
            comments_parts.append(f"### Code Cleanliness\n{cleanliness_feedback}")
        
        if communication_feedback and "placeholder" not in communication_feedback.lower():
            comments_parts.append(f"### Communication\n{communication_feedback}")
        
        if efficiency_feedback:
            comments_parts.append(f"### Efficiency\n{efficiency_feedback}")
        
        if overall_feedback:
            comments_parts.append(f"### Overall Comments\n{overall_feedback}")
        
        # Join with double line breaks for readability
        comments = "\n\n".join(comments_parts) if comments_parts else eval_text
        
        return FeedbackReport(
            communication=communication,
            codeCleanliness=code_cleanliness,
            codeEfficiency=efficiency,
            comments=comments,
        )
    except Exception as exc:
        # Log the error and return a fallback response
        import logging
        logging.error(f"Error evaluating code: {exc}")
        raise HTTPException(500, f"Failed to evaluate code: {str(exc)}")