"""
Configuration helpers for the workflow service.
The logic mirrors the original workflow/config.py but now lives inside the
app.services.workflow package so other modules can import settings without
dragging in unrelated globals.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Create .env from .env.example and set it.")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default)


ANTHROPIC_API_KEY = _required("ANTHROPIC_API_KEY")
ELEVENLABS_API_KEY = _required("ELEVENLABS_API_KEY")
DEEPGRAM_API_KEY = _optional("DEEPGRAM_API_KEY", "")  # Keep for STT if needed

ANTHROPIC_MODEL = _optional("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

# ElevenLabs TTS settings
ELEVENLABS_VOICE_ID = _optional("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel
ELEVENLABS_MODEL = _optional("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
ELEVENLABS_OUTPUT_FORMAT = _optional("ELEVENLABS_OUTPUT_FORMAT", "pcm_16000")  # PCM 16kHz for compatibility

# Deepgram settings (kept for STT)
DEEPGRAM_TTS_VOICE = _optional("DEEPGRAM_TTS_VOICE", "aura-2-thalia-en")
DEEPGRAM_STREAM_ENCODING = _optional("DEEPGRAM_STREAM_ENCODING", "linear16")
DEEPGRAM_SAMPLE_RATE = int(_optional("DEEPGRAM_SAMPLE_RATE", "48000"))
DEEPGRAM_STT_MODEL = _optional("DEEPGRAM_STT_MODEL", "nova-3")

TTS_LIVE_JSON_PATH = _optional("TTS_LIVE_JSON_PATH", "live_tts_captions.ndjson")
LIVE_TRANSCRIPTION_PATH = _optional("LIVE_TRANSCRIPTION_PATH", "live_transcription.json")
LIVE_TRANSCRIPTION_UPDATE_INTERVAL = float(_optional("LIVE_TRANSCRIPTION_UPDATE_INTERVAL", "2.0"))

_cors = _optional("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:5173")
CORS_ALLOW_ORIGINS = [origin.strip() for origin in _cors.split(",") if origin.strip()] or ["*"]
