"""Chatbot package exports.

This package contains a thin Claude client, prompt builders, a TTS
sanitizer/adapter and a small Agent façade to be used by FastAPI
endpoints. It is intentionally lightweight so the existing endpoints
in `workflow/api.py` can be incrementally refactored to import from
here.
"""
from .agent import ChatbotAgent
from .claude_client import ClaudeClient
from .prompts import build_system_prompt_from_question, load_question_by_difficulty
from .tts_adapter import sanitize_for_tts

__all__ = [
    "ChatbotAgent",
    "ClaudeClient",
    "build_system_prompt_from_question",
    "load_question_by_difficulty",
    "sanitize_for_tts",
]
