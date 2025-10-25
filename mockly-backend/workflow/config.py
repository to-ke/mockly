import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing {name}. Create .env from .env.example and set it.")
    return v

def _opt(name: str, default: str = "") -> str:
    return os.getenv(name, default)

# required secrets
ANTHROPIC_API_KEY = _req("ANTHROPIC_API_KEY")
DEEPGRAM_API_KEY  = _req("DEEPGRAM_API_KEY")

# model/voice defaults
ANTHROPIC_MODEL     = _opt("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
DEEPGRAM_TTS_VOICE  = _opt("DEEPGRAM_TTS_VOICE", "aura-asteria-en")
DEEPGRAM_TTS_FORMAT = _opt("DEEPGRAM_TTS_FORMAT", "mp3")   # per docs, default is mp3
DEEPGRAM_STT_MODEL  = _opt("DEEPGRAM_STT_MODEL", "nova-3")
