"""
Anthropic streaming helpers.
"""

from __future__ import annotations

from typing import Iterable

from .clients import anthropic_client
from .config import ANTHROPIC_MODEL
from .prompts import build_system_prompt_from_question


def stream_claude_text(user_text: str, system_override: str | None = None) -> Iterable[str]:
    """
    Stream text chunks from Claude using the Anthropic SDK's iterator API.
    """
    with anthropic_client.messages.stream(
        model=ANTHROPIC_MODEL,
        system=(system_override or build_system_prompt_from_question({})),
        messages=[{"role": "user", "content": user_text}],
        max_tokens=1024,
    ) as stream:
        for piece in getattr(stream, "text_stream", []) or []:
            if piece:
                yield piece


__all__ = ["stream_claude_text"]
