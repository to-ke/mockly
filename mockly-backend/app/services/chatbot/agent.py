"""Thin ChatbotAgent façade.

Provides a small surface that previously lived inline in
`workflow/api.py`: stream_text, get_text and stream_audio. The agent
composes the Claude client, prompt builder and TTS adapter so the
FastAPI endpoints can be switched to call into this module.
"""
from typing import Iterable, AsyncIterator
import asyncio

from .claude_client import ClaudeClient
from .prompts import build_system_prompt_from_question
from .tts_adapter import DeepgramTTSAdapter


def sentence_chunks(token_iter: Iterable[str], min_chars: int = 24, first_flush_ms: int = 900) -> Iterable[str]:
    """Chunk a token iterator into sentence-like pieces.

    Logic mirrors the version used in `workflow/api.py` so auditory
    flushing behavior is preserved when moving endpoints over.
    """
    import re, time

    buf, acc = [], 0
    first_started_at = None
    first_chunk_sent = False

    for tok in token_iter:
        if first_started_at is None:
            first_started_at = time.perf_counter()
        buf.append(tok)
        acc += len(tok)
        joined = "".join(buf)

        if re.search(r"[.!?]\s$", joined) or "\n" in joined or acc >= min_chars:
            out = joined.strip()
            if out:
                yield out
                first_chunk_sent = True
            buf, acc, first_started_at = [], 0, None
            continue

        if not first_chunk_sent and first_started_at is not None:
            elapsed_ms = (time.perf_counter() - first_started_at) * 1000.0
            if elapsed_ms >= first_flush_ms and joined.strip():
                yield joined.strip()
                buf, acc, first_started_at = [], 0, None
                first_chunk_sent = True

    if buf:
        out = "".join(buf).strip()
        if out:
            yield out


class ChatbotAgent:
    """Small façade combining Claude and TTS behavior.

    Methods (minimum):
      - stream_text(user_text, question) -> Iterable[str]
      - get_text(user_text, question) -> str
      - stream_audio(user_text, question) -> AsyncIterator[bytes]
    """

    def __init__(self, claude: ClaudeClient | None = None, tts: DeepgramTTSAdapter | None = None) -> None:
        self.claude = claude or ClaudeClient()
        self.tts = tts or DeepgramTTSAdapter()

    def stream_text(self, user_text: str, question: dict | None = None) -> Iterable[str]:
        system = build_system_prompt_from_question(question)
        return self.claude.stream_text(user_text, system=system)

    def get_text(self, user_text: str, question: dict | None = None) -> str:
        system = build_system_prompt_from_question(question)
        return self.claude.create_text(user_text, system=system)

    async def stream_audio(self, user_text: str, question: dict | None = None) -> AsyncIterator[bytes]:
        """Composite: stream Claude tokens -> chunk -> Deepgram TTS frames.

        Returns an async iterator of raw PCM frames (bytes). This mirrors
        the `/type/stream` and `/input/stream` pipeline in
        `workflow/api.py`.
        """
        system = build_system_prompt_from_question(question)
        tokens = self.claude.stream_text(user_text, system=system)
        chunks = sentence_chunks(tokens)
        async for audio in self.tts.stream(chunks):
            yield audio


__all__ = ["ChatbotAgent", "sentence_chunks"]
