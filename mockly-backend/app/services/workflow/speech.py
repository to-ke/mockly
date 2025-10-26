"""
Text post-processing utilities for the TTS pipeline.
"""

from __future__ import annotations

import re
import time
from typing import Iterable


def sentence_chunks(token_iter: Iterable[str], min_chars: int = 24, first_flush_ms: int = 900) -> Iterable[str]:
    """
    Chunk streamed tokens into sentence-like fragments to reduce TTS latency.
    """
    buffer: list[str] = []
    buffer_len = 0
    first_started_at: float | None = None
    first_chunk_sent = False

    for token in token_iter:
        if first_started_at is None:
            first_started_at = time.perf_counter()

        buffer.append(token)
        buffer_len += len(token)
        joined = "".join(buffer)

        if re.search(r"[.!?]\s$", joined) or "\n" in joined or buffer_len >= min_chars:
            out = joined.strip()
            if out:
                yield out
                first_chunk_sent = True
            buffer, buffer_len, first_started_at = [], 0, None
            continue

        if not first_chunk_sent and first_started_at is not None:
            elapsed_ms = (time.perf_counter() - first_started_at) * 1000.0
            if elapsed_ms >= first_flush_ms and joined.strip():
                yield joined.strip()
                buffer, buffer_len, first_started_at = [], 0, None
                first_chunk_sent = True

    if buffer:
        out = "".join(buffer).strip()
        if out:
            yield out


def sanitize_for_tts(text: str) -> str:
    """
    Remove markdown and formatting markers so the generated speech sounds natural.
    """
    if not text:
        return ""
    text = re.sub(r"```+", "", text)
    text = text.replace("`", "")
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"</?[^>\n]+>", "", text)
    text = re.sub(r"\*{2,}", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


__all__ = ["sentence_chunks", "sanitize_for_tts"]
