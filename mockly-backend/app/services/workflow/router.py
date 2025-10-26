from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import AsyncIterator

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from .claude import stream_claude_text
from .clients import anthropic_client, deepgram_client as dg
from .config import (
    ANTHROPIC_MODEL,
    DEEPGRAM_SAMPLE_RATE,
    DEEPGRAM_STREAM_ENCODING,
    DEEPGRAM_TTS_VOICE,
)
from .evaluation import parse_evaluation_scores
from .prompts import build_system_prompt_from_question
from .questions import load_question_by_difficulty
from .speech import sanitize_for_tts, sentence_chunks
from .transcription import transcribe_prerecorded_deepgram
from .tts import stream_deepgram_tts, stream_deepgram_tts_raw

router = APIRouter(tags=["workflow"])


def _resolve_question(payload: dict) -> dict | None:
    question = payload.get("question")
    if not question and payload.get("difficulty"):
        question = load_question_by_difficulty(str(payload.get("difficulty")))
    return question


def _resolve_user_text(payload: dict, question: dict | None) -> str:
    user_text = (payload.get("text") or "").strip()
    if not user_text:
        if payload.get("difficulty") or question:
            return "BEGIN INTERVIEW"
        raise HTTPException(400, "Field 'text' is required.")
    return user_text


def _stream_media_response(generator: AsyncIterator[bytes]):
    return StreamingResponse(
        generator,
        media_type=f"audio/L16; rate={DEEPGRAM_SAMPLE_RATE}; channels=1",
    )


@router.post("/type/stream")
def type_streaming(payload: dict = Body(...)):
    question = _resolve_question(payload)
    system = build_system_prompt_from_question(question)
    user_text = _resolve_user_text(payload, question)

    async def audio_iter():
        tokens = stream_claude_text(user_text, system_override=system)
        chunks = sentence_chunks(tokens)
        async for audio in stream_deepgram_tts_raw(chunks):
            yield audio

    return _stream_media_response(audio_iter())


@router.get("/debug/tts")
async def debug_tts():
    async def audio_iter():
        test_sentences = [
            "Testing the voice connection. You should hear this shortly.",
            "If you can hear this, Deepgram streaming is working.",
        ]
        async for audio in stream_deepgram_tts(test_sentences):
            yield audio

    return _stream_media_response(audio_iter())


@router.get("/debug/tts-min")
async def debug_tts_min():
    from deepgram.extensions.types.sockets import (  # type: ignore
        SpeakV1ControlMessage,
        SpeakV1SocketClientResponse,
        SpeakV1TextMessage,
    )

    async def audio_iter():
        q: asyncio.Queue[bytes] = asyncio.Queue()
        closed = {"flag": False}

        def on_message(msg: SpeakV1SocketClientResponse):
            if isinstance(msg, bytes):
                q.put_nowait(msg)
                return
            mtype = getattr(msg, "type", None) or getattr(msg, "_type", None)
            data = getattr(msg, "data", None)
            if str(mtype).lower() == "audio" and isinstance(data, (bytes, bytearray)):
                q.put_nowait(bytes(data))
                return
            logging.info("[Deepgram WS] non-audio: %r", msg)

        with dg.speak.v1.connect(
            model=DEEPGRAM_TTS_VOICE,
            encoding=DEEPGRAM_STREAM_ENCODING,
            sample_rate=DEEPGRAM_SAMPLE_RATE,
        ) as ws:
            ws.on(EventType.OPEN, lambda _: logging.info("[Deepgram WS] OPEN"))
            ws.on(EventType.MESSAGE, on_message)
            ws.on(EventType.CLOSE, lambda _: (closed.update({"flag": True}), logging.info("[Deepgram WS] CLOSE")))
            ws.on(EventType.ERROR, lambda exc: logging.error("[Deepgram WS] ERROR: %s", exc))
            ws.start_listening()

            text = "This is a streaming test from Deepgram continuous text."
            ws.send_text(SpeakV1TextMessage(text=text))
            logging.info("[Deepgram WS] SENT Text: %r", text)
            ws.send_control(SpeakV1ControlMessage(type="Flush"))
            logging.info("[Deepgram WS] SENT Flush")
            await asyncio.sleep(0.1)
            ws.send_control(SpeakV1ControlMessage(type="Close"))
            logging.info("[Deepgram WS] SENT Close")

            last = time.perf_counter()
            got_any = False
            while True:
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=0.8)
                    got_any = True
                    last = time.perf_counter()
                    yield frame
                except asyncio.TimeoutError:
                    if closed["flag"] and (time.perf_counter() - last) > 0.8:
                        break

            if not got_any:
                logging.warning("[Deepgram WS] no audio frames received in tts-min")

    from deepgram.core.events import EventType  # imported lazily to avoid unused dep at import

    return _stream_media_response(audio_iter())


@router.post("/debug/claude/stream")
def debug_claude_stream(payload: dict = Body(...)):
    question = _resolve_question(payload)
    system = build_system_prompt_from_question(question)
    user_text = _resolve_user_text(payload, question)

    def iter_text():
        yield from stream_claude_text(user_text, system_override=system)

    return StreamingResponse(iter_text(), media_type="text/plain; charset=utf-8")


@router.get("/debug/tts-direct")
async def debug_tts_direct():
    async def audio_iter():
        async def one_sentence():
            yield "This is a direct Speak test."

        async for chunk in stream_deepgram_tts(one_sentence()):
            yield chunk

    return _stream_media_response(audio_iter())


@router.get("/debug/tts-raw")
async def debug_tts_raw():
    from deepgram.core.events import EventType  # imported lazily

    q: asyncio.Queue[bytes] = asyncio.Queue()
    closed = {"flag": False}

    def on_message(msg):
        if isinstance(msg, (bytes, bytearray)):
            q.put_nowait(bytes(msg))
            return
        mtype = getattr(msg, "type", None) or getattr(msg, "_type", None)
        data = getattr(msg, "data", None)
        if str(mtype).lower() == "audio" and isinstance(data, (bytes, bytearray)):
            q.put_nowait(bytes(data))
            return
        logging.info("[Deepgram WS] non-audio: %r", msg)

    def open_ws():
        return dg.speak.v1.connect(
            model=DEEPGRAM_TTS_VOICE,
            encoding=DEEPGRAM_STREAM_ENCODING,
            sample_rate=DEEPGRAM_SAMPLE_RATE,
        )

    async def audio_iter():
        with open_ws() as ws:
            ws.on(EventType.OPEN, lambda _: logging.info("[Deepgram WS] OPEN"))
            ws.on(EventType.MESSAGE, on_message)
            ws.on(EventType.CLOSE, lambda _: (closed.update({"flag": True}), logging.info("[Deepgram WS] CLOSE")))
            ws.on(EventType.ERROR, lambda exc: logging.error("[Deepgram WS] ERROR: %s", exc))
            ws.start_listening()

            speak_payload = json.dumps({"type": "Speak", "text": "This is a direct Speak test."})
            ws.send_text(speak_payload)
            logging.info("[Deepgram WS] SENT Speak: %s", speak_payload)

            ws.send_text(json.dumps({"type": "Flush"}))
            logging.info("[Deepgram WS] SENT Flush")

            await asyncio.sleep(0.05)

            ws.send_text(json.dumps({"type": "Close"}))
            logging.info("[Deepgram WS] SENT Close")

            last = time.perf_counter()
            while True:
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=0.8)
                    yield frame
                    last = time.perf_counter()
                except asyncio.TimeoutError:
                    if closed["flag"] and (time.perf_counter() - last) > 0.8:
                        break

    return _stream_media_response(audio_iter())


@router.post("/type")
async def type_to_voice(request: Request):
    data = await request.json()
    question = _resolve_question(data)
    system = build_system_prompt_from_question(question)
    user_text = _resolve_user_text(data, question)

    message = anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        system=system,
        messages=[{"role": "user", "content": user_text}],
        max_tokens=800,
    )
    full_text = "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    )
    full_text = sanitize_for_tts(full_text)

    try:
        generated = dg.speak.v1.audio.generate(
            text=full_text,
            model=DEEPGRAM_TTS_VOICE,
            encoding="mp3",
        )
        audio: bytes | None = None
        stream_attr = getattr(generated, "stream", None)
        if stream_attr is not None and hasattr(stream_attr, "getvalue"):
            audio = stream_attr.getvalue()
        elif isinstance(generated, (bytes, bytearray)):
            audio = bytes(generated)
        else:
            try:
                parts = []
                for piece in generated:  # type: ignore
                    if isinstance(piece, (bytes, bytearray)):
                        parts.append(bytes(piece))
                audio = b"".join(parts) if parts else None
            except TypeError:
                audio = None
        if not audio:
            raise RuntimeError("Deepgram TTS returned no audio bytes")
    except Exception as exc:
        logging.exception("Deepgram TTS generation failed: %s", exc)
        raise HTTPException(500, "TTS generation failed") from exc

    return Response(content=audio, media_type="audio/mpeg")


@router.get("/health")
def health():
    return {"ok": True}


@router.post("/eval/parse")
async def eval_parse(request: Request):
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "Field 'text' is required.")
    return {"scores": parse_evaluation_scores(text)}


@router.post("/input/stream")
def input_stream(payload: dict = Body(...)):
    mode = (payload.get("mode") or "text").strip().lower()
    question = _resolve_question(payload)
    system = build_system_prompt_from_question(question)

    async def audio_iter():
        if mode == "voice":
            user_text = await _handle_voice_payload(payload)
        else:
            user_text = _resolve_user_text(payload, question)

        tokens = stream_claude_text(user_text, system_override=system)
        chunks = sentence_chunks(tokens)
        async for audio in stream_deepgram_tts_raw(chunks):
            yield audio

    return _stream_media_response(audio_iter())


async def _handle_voice_payload(payload: dict) -> str:
    b64_audio = payload.get("audio_b64")
    if not b64_audio:
        raise HTTPException(400, "audio_b64 required for voice mode")
    try:
        audio_bytes = base64.b64decode(b64_audio)
    except Exception as exc:
        raise HTTPException(400, "audio_b64 is invalid base64") from exc

    mime = (payload.get("mime") or "audio/wav").strip() or "audio/wav"
    try:
        transcript = await transcribe_prerecorded_deepgram(audio_bytes, content_type=mime)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    if not transcript:
        raise HTTPException(400, "Transcription returned empty text")
    return transcript
