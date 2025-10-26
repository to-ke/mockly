"""
Deepgram STT helpers for prerecorded audio.

Provides a simple text transcript helper and a detailed variant that
returns utterances and word timestamps when enabled via Deepgram's
`utterances`, `diarize`, and `smart_format` parameters.
"""

from __future__ import annotations

import logging

import httpx

from .config import DEEPGRAM_API_KEY, DEEPGRAM_STT_MODEL


async def transcribe_prerecorded_deepgram(audio_bytes: bytes, content_type: str = "audio/wav") -> str:
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": content_type,
    }
    params = {"model": DEEPGRAM_STT_MODEL}
    url = "https://api.deepgram.com/v1/listen"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, params=params, headers=headers, content=audio_bytes)
        response.raise_for_status()
        data = response.json()
    try:
        return data["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception:
        logging.error("Unexpected Deepgram STT response: %s", data)
        raise RuntimeError("STT failed to return transcript")


async def transcribe_prerecorded_deepgram_detailed(
    audio_bytes: bytes,
    *,
    content_type: str = "audio/wav",
    utterances: bool = True,
    diarize: bool = True,
    smart_format: bool = True,
) -> dict:
    """
    Call Deepgram's `v1/listen` with options that return timestamps.

    Returns a dict containing Deepgram's parsed JSON `results` section,
    including `utterances[]` with {start, end, transcript, words[]} when
    `utterances=True`, and per-word {start, end} when available.
    """
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": content_type,
    }
    params = {
        "model": DEEPGRAM_STT_MODEL,
        # Deepgram accepts booleans here; httpx will serialize to 'true'/'false'.
        "utterances": utterances,
        "diarize": diarize,
        "smart_format": smart_format,
    }
    url = "https://api.deepgram.com/v1/listen"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, params=params, headers=headers, content=audio_bytes)
        response.raise_for_status()
        data = response.json()

    results = data.get("results") or {}
    # Minimal validation: ensure the shape contains either utterances or channels.
    if not results:
        logging.error("Deepgram STT detailed: missing results: %s", data)
        raise RuntimeError("STT detailed response missing results")
    return results


__all__ = [
    "transcribe_prerecorded_deepgram",
    "transcribe_prerecorded_deepgram_detailed",
]
