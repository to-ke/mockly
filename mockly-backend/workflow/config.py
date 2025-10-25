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

# Required secrets
ANTHROPIC_API_KEY   = _req("ANTHROPIC_API_KEY")
DEEPGRAM_API_KEY    = _req("DEEPGRAM_API_KEY")

# Claude config
ANTHROPIC_MODEL     = _opt("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

# Deepgram TTS WS config
DEEPGRAM_TTS_VOICE      = _opt("DEEPGRAM_TTS_VOICE", "aura-2-thalia-en")
DEEPGRAM_STREAM_ENCODING= _opt("DEEPGRAM_STREAM_ENCODING", "linear16")   # linear16|mulaw|alaw
DEEPGRAM_SAMPLE_RATE    = int(_opt("DEEPGRAM_SAMPLE_RATE", "48000"))

# (Optional) STT model if/when you add streaming STT later
DEEPGRAM_STT_MODEL  = _opt("DEEPGRAM_STT_MODEL", "nova-3")
