# API Call# api.py — SDK-only: Vapi/URL -> Deepgram STT -> Claude -> Deepgram TTS
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import Response as FastAPIResponse
from anthropic import Anthropic
from deepgram import DeepgramClient
from deepgram.core.errors import DeepgramApiError

from config import (
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    DEEPGRAM_API_KEY, DEEPGRAM_STT_MODEL,
    DEEPGRAM_TTS_VOICE, DEEPGRAM_TTS_FORMAT,
)

app = FastAPI(title="Local Voice/Text Assistant (SDK-only)")

# ---------- SDK clients ----------
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
dg = DeepgramClient(api_key=DEEPGRAM_API_KEY)

# ---------- Claude (Messages API via Anthropic SDK) ----------
def claude_complete(text: str) -> str:
    """Non-streaming for simplicity (you can switch to SDK streaming later)."""
    msg = anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": text}],
    )
    # concatenate text blocks
    return "".join([b.text for b in msg.content if getattr(b, "type", "") == "text"])

# ---------- Deepgram STT (SDK; pre-recorded by URL) ----------
def deepgram_transcribe_url(audio_url: str) -> str:
    """
    Uses Deepgram SDK to transcribe a remote audio URL with a nova* model.
    Docs show prerecorded STT via SDK; 'model' is required. 
    """
    try:
        # modern SDK exposes a media.transcribe_url method
        res = dg.listen.v1.media.transcribe_url(
            url=audio_url,
            model=DEEPGRAM_STT_MODEL,
            smart_format=True,
        )
        # best path typical per docs
        return res.results.channels[0].alternatives[0].transcript
    except DeepgramApiError as e:
        raise HTTPException(status_code=502, detail=f"Deepgram STT error: {e}")

# ---------- Deepgram TTS (SDK) ----------
def deepgram_tts(text: str) -> bytes:
    """
    Uses Deepgram SDK to synthesize speech with Aura voice.
    For models/voices & encoding see docs (e.g., aura-asteria-en, mp3/wav). 
    """
    try:
        # v4+ SDK supports speak.v1.audio.generate(text=..., model=..., encoding=...)
        resp = dg.speak.v1.audio.generate(
            text=text,
            model=DEEPGRAM_TTS_VOICE,    # e.g., "aura-asteria-en" or newer "aura-2-<voice>-en"
            encoding=DEEPGRAM_TTS_FORMAT # "mp3" (default) | "wav" | "linear16"
        )
        return resp.stream.getvalue()   # bytes buffer
    except DeepgramApiError as e:
        raise HTTPException(status_code=502, detail=f"Deepgram TTS error: {e}")

# ---------- Flow 1: Vapi -> (Deepgram STT) -> Claude -> Deepgram TTS ----------
@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    event = await request.json()
    # Vapi may pass transcript text directly, else provide a remote audio URL
    transcript = (event.get("transcript") or event.get("text") or "").strip()
    audio_url = event.get("audio_url") or event.get("recording_url")

    if not transcript:
        if not audio_url:
            raise HTTPException(400, "Provide 'transcript' or 'audio_url' in Vapi event.")
        transcript = deepgram_transcribe_url(audio_url)

    reply_text = claude_complete(transcript)
    audio_bytes = deepgram_tts(reply_text)
    media_type = "audio/mpeg" if DEEPGRAM_TTS_FORMAT == "mp3" else f"audio/{DEEPGRAM_TTS_FORMAT}"
    return FastAPIResponse(content=audio_bytes, media_type=media_type)

# ---------- Flow 2: Text -> Claude -> Deepgram TTS ----------
@app.post("/type")
async def type_to_voice(request: Request):
    data = await request.json()
    user_text = (data.get("text") or "").strip()
    if not user_text:
        raise HTTPException(400, "Field 'text' is required.")

    reply_text = claude_complete(user_text)
    audio_bytes = deepgram_tts(reply_text)
    media_type = "audio/mpeg" if DEEPGRAM_TTS_FORMAT == "mp3" else f"audio/{DEEPGRAM_TTS_FORMAT}"
    return Response(content=audio_bytes, media_type=media_type)

# Run: uvicorn api:app --reload
