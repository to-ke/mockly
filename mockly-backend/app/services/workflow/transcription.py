"""
Deepgram STT helper for prerecorded audio.
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


__all__ = ["transcribe_prerecorded_deepgram"]
