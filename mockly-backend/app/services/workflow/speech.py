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
    import logging
    
    buffer: list[str] = []
    buffer_len = 0
    first_started_at: float | None = None
    first_chunk_sent = False
    total_tokens_received = 0

    for token in token_iter:
        total_tokens_received += 1
        
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

    # Flush any remaining buffer
    if buffer:
        out = "".join(buffer).strip()
        if out:
            logging.info(f"[sentence_chunks] Flushing final buffer: {len(out)} chars")
            yield out
    
    logging.info(f"[sentence_chunks] Processed {total_tokens_received} tokens total")


def sanitize_for_tts(text: str) -> str:
    """
    Aggressively sanitize text for TTS, removing code syntax and special characters
    that confuse Deepgram. Keep only basic punctuation for natural speech.
    """
    if not text:
        return ""
    
    # Log original text for debugging
    import logging
    original_text = text[:200] if len(text) > 200 else text
    
    # Remove code blocks entirely (including content)
    text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
    text = re.sub(r"```+", "", text)
    
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    text = text.replace("`", "")
    
    # Remove markdown formatting
    text = text.replace("**", "").replace("__", "").replace("*", "")
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.M)
    
    # Remove XML/HTML-like tags
    text = re.sub(r"</?[^>\n]+>", "", text)
    
    # Remove list markers
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)
    
    # Remove/replace code syntax characters that confuse TTS
    # Remove brackets and braces (but keep content)
    text = text.replace("[", "").replace("]", "")
    text = text.replace("{", "").replace("}", "")
    text = text.replace("(", "").replace(")", "")
    
    # Remove programming symbols
    text = text.replace("=>", " ")
    text = text.replace("->", " to ")
    text = text.replace("==", " equals ")
    text = text.replace("!=", " not equals ")
    text = text.replace("<=", " less than or equal to ")
    text = text.replace(">=", " greater than or equal to ")
    text = text.replace("++", " plus plus ")
    text = text.replace("--", " minus minus ")
    
    # Remove other special characters (keep basic punctuation: . , ! ? : ; ' " -)
    text = re.sub(r"[&@#$%^+=<>|\\~/]", " ", text)
    
    # Remove underscores (often in variable names)
    text = text.replace("_", " ")
    
    # Clean up quotes to standard style
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    
    # Remove excessive punctuation
    text = re.sub(r"\.{2,}", ".", text)  # Multiple dots -> single dot
    text = re.sub(r"\!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)
    
    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Max 2 newlines
    text = re.sub(r"\s+([.,!?:;])", r"\1", text)  # Remove space before punctuation
    
    result = text.strip()
    
    # Log if significant changes were made
    if len(original_text) > 0 and abs(len(result) - len(original_text)) > 50:
        logging.info(f"[sanitize_for_tts] Removed {len(original_text) - len(result)} chars")
        logging.debug(f"[sanitize_for_tts] Before: {original_text}")
        logging.debug(f"[sanitize_for_tts] After: {result[:200]}")
    
    return result


__all__ = ["sentence_chunks", "sanitize_for_tts"]
