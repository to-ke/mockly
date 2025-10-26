"""Thin Anthropic / Claude client helpers.

This module provides a small wrapper around the Anthropic SDK used in
`workflow/api.py`. It purposefully mirrors the streaming helper used
there so you can incrementally switch imports.
"""
from typing import Iterable
import logging

from anthropic import Anthropic

from workflow.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Minimal Claude client wrapper.

    Methods:
      - stream_text(user_text, system) -> Iterable[str]
      - create_text(user_text, system, max_tokens=800) -> str
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or ANTHROPIC_MODEL
        self._client = Anthropic(api_key=self.api_key)

    def stream_text(self, user_text: str, system: str | None = None, max_tokens: int = 1024) -> Iterable[str]:
        """Yield streaming text pieces from Claude.

        This mirrors the pattern used in `workflow/api.py` so it can be
        dropped in without changing endpoint signatures.
        """
        with self._client.messages.stream(
            model=self.model,
            system=(system or ""),
            messages=[{"role": "user", "content": user_text}],
            max_tokens=max_tokens,
        ) as stream:
            for piece in getattr(stream, "text_stream", []) or []:
                if piece:
                    yield piece

    def create_text(self, user_text: str, system: str | None = None, max_tokens: int = 800) -> str:
        """Non-streaming completion: returns full text string.

        Note: Anthropic SDK returns a richer structure; this method
        extracts text parts similarly to the existing api.py code.
        """
        msg = self._client.messages.create(
            model=self.model,
            system=(system or ""),
            messages=[{"role": "user", "content": user_text}],
            max_tokens=max_tokens,
        )
        parts = []
        for b in msg.content:
            try:
                if getattr(b, "type", "") == "text":
                    parts.append(b.text)
            except Exception:
                # Best-effort extraction
                try:
                    parts.append(str(b))
                except Exception:
                    pass
        return "".join(parts)


__all__ = ["ClaudeClient"]
