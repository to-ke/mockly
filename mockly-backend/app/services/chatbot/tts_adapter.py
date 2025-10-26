"""TTS sanitation and TTS adapters.

This module provides `sanitize_for_tts` and TTS adapters for both
Deepgram and ElevenLabs. The implementation is intentionally similar to
the helpers in `workflow/api.py` so it can be used as a drop-in replacement.
"""
from typing import Iterable, AsyncIterator
import re
import contextlib
import asyncio
import logging
import time
from deepgram import DeepgramClient
from deepgram.core.events import EventType
from app.services.workflow.config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_TTS_VOICE,
    DEEPGRAM_STREAM_ENCODING,
    DEEPGRAM_SAMPLE_RATE,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL,
    ELEVENLABS_OUTPUT_FORMAT,
)

logger = logging.getLogger(__name__)


def sanitize_for_tts(text: str) -> str:
    if not text:
        return ""
    # Remove code fences/backticks
    text = re.sub(r"```+", "", text)
    text = text.replace("`", "")
    # Remove bold/italics markers
    text = text.replace("**", "").replace("__", "")
    # Strip markdown headings at line starts
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    # Remove xml/html-like tags
    text = re.sub(r"</?[^>\n]+>", "", text)
    # Collapse repeated asterisks
    text = re.sub(r"\*{2,}", "", text)
    # Normalize excess spaces (keep newlines)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


class DeepgramTTSAdapter:
    """Adapter to stream audio from Deepgram's streaming TTS API.

    Methods:
      - stream(sentences) -> AsyncIterator[bytes]

    The adapter uses the official Deepgram client when available.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or DEEPGRAM_API_KEY
        self.client = DeepgramClient(api_key=self.api_key)

    async def stream(self, sentences: Iterable[str]) -> AsyncIterator[bytes]:
        """Stream raw audio frames from Deepgram as bytes.

        This implements the same high-level flow as the existing
        `stream_deepgram_tts` helper in `workflow/api.py`.
        """
        q: asyncio.Queue[bytes] = asyncio.Queue()
        closed = {"flag": False}
        saw_audio = {"flag": False}

        def on_message(msg):
            # audio bytes may arrive as raw bytes
            if isinstance(msg, (bytes, bytearray)):
                saw_audio["flag"] = True
                q.put_nowait(bytes(msg));
                return
            mtype = getattr(msg, "type", None) or getattr(msg, "_type", None)
            data = getattr(msg, "data", None)
            if str(mtype).lower() == "audio" and isinstance(data, (bytes, bytearray)):
                saw_audio["flag"] = True
                q.put_nowait(bytes(data));
                return
            logger.info(f"[Deepgram WS] non-audio: {msg!r}")

        with self.client.speak.v1.connect(
            model=DEEPGRAM_TTS_VOICE,
            encoding=DEEPGRAM_STREAM_ENCODING,
            sample_rate=DEEPGRAM_SAMPLE_RATE,
        ) as ws:
            ws.on(EventType.OPEN, lambda _: logger.info("[Deepgram WS] OPEN"))
            ws.on(EventType.MESSAGE, on_message)
            ws.on(EventType.CLOSE, lambda _: (closed.update({"flag": True}), logger.info("[Deepgram WS] CLOSE")))
            ws.on(EventType.ERROR, lambda e: logger.error(f"[Deepgram WS] ERROR: {e}"))
            ws.start_listening()

            async def _send_chunks():
                try:
                    FLUSH_CHARS = 220
                    FLUSH_MS = 650
                    last_flush = asyncio.get_event_loop().time()
                    pending_chars = 0
                    if hasattr(sentences, "__aiter__"):
                        async for sentence in sentences:  # type: ignore[attr-defined]
                            clean = sanitize_for_tts(str(sentence)).strip()
                            if not clean:
                                continue
                            ws.send_text({"type": "Speak", "text": clean})
                            pending_chars += len(clean)
                            now = asyncio.get_event_loop().time()
                            if pending_chars >= FLUSH_CHARS or (now - last_flush) * 1000.0 >= FLUSH_MS:
                                ws.send_text({"type": "Flush"})
                                pending_chars = 0
                                last_flush = now
                            await asyncio.sleep(0)
                    else:
                        for sentence in sentences:  # type: ignore
                            clean = sanitize_for_tts(str(sentence)).strip()
                            if not clean:
                                continue
                            ws.send_text({"type": "Speak", "text": clean})
                            pending_chars += len(clean)
                            now = asyncio.get_event_loop().time()
                            if pending_chars >= FLUSH_CHARS or (now - last_flush) * 1000.0 >= FLUSH_MS:
                                ws.send_text({"type": "Flush"})
                                pending_chars = 0
                                last_flush = now
                            await asyncio.sleep(0)
                except Exception:
                    pass

            send_task = asyncio.create_task(_send_chunks())

            last = asyncio.get_event_loop().time(); total = 0
            try:
                while True:
                    try:
                        frame = await asyncio.wait_for(q.get(), timeout=0.8)
                        total += len(frame)
                        yield frame
                        last = asyncio.get_event_loop().time()
                    except asyncio.TimeoutError:
                        if closed["flag"] and (asyncio.get_event_loop().time() - last) > 0.8:
                            break

                if not send_task.done():
                    send_task.cancel()
                    with contextlib.suppress(Exception):
                        await send_task
            finally:
                with contextlib.suppress(Exception):
                    ws.send_text({"type": "Flush"})
                with contextlib.suppress(Exception):
                    ws.send_text({"type": "Close"})

        if not saw_audio["flag"]:
            logger.warning("[Deepgram WS] no audio frames were received")


class ElevenLabsTTSAdapter:
    """Adapter to stream audio from ElevenLabs TTS API.

    Methods:
      - stream(sentences) -> AsyncIterator[bytes]

    The adapter uses the official ElevenLabs client.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ELEVENLABS_API_KEY

    async def stream(self, sentences: Iterable[str]) -> AsyncIterator[bytes]:
        """Stream raw audio frames from ElevenLabs as bytes.

        This implements streaming TTS using ElevenLabs API.
        """
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency 'elevenlabs'. Install with: pip install elevenlabs"
            ) from exc

        logger.info(f"[ElevenLabs TTS] Initializing with voice={ELEVENLABS_VOICE_ID}, model={ELEVENLABS_MODEL}")

        client = ElevenLabs(api_key=self.api_key)

        # Collect sentences to send as a batch for better streaming
        sentence_buffer = []

        if hasattr(sentences, "__aiter__"):
            async for sentence in sentences:  # type: ignore[attr-defined]
                clean = sanitize_for_tts(str(sentence)).strip()
                if clean:
                    sentence_buffer.append(clean)
        else:
            for sentence in sentences:  # type: ignore
                clean = sanitize_for_tts(str(sentence)).strip()
                if clean:
                    sentence_buffer.append(clean)

        if not sentence_buffer:
            logger.warning("[ElevenLabs TTS] No sentences to synthesize")
            return

        full_text = " ".join(sentence_buffer)
        logger.info(f"[ElevenLabs TTS] Synthesizing {len(full_text)} characters across {len(sentence_buffer)} sentences")

        try:
            # Use streaming API for low latency
            audio_stream = client.text_to_speech.convert_as_stream(
                voice_id=ELEVENLABS_VOICE_ID,
                text=full_text,
                model_id=ELEVENLABS_MODEL,
                output_format=ELEVENLABS_OUTPUT_FORMAT,
            )

            total_bytes = 0
            chunk_count = 0
            start_time = time.perf_counter()

            for chunk in audio_stream:
                if chunk:
                    total_bytes += len(chunk)
                    chunk_count += 1
                    if chunk_count == 1:
                        first_chunk_time = time.perf_counter() - start_time
                        logger.info(f"[ElevenLabs TTS] First audio chunk after {first_chunk_time*1000:.1f}ms")
                    yield chunk
                    # Allow other async tasks to run
                    await asyncio.sleep(0)

            elapsed = time.perf_counter() - start_time
            logger.info(f"[ElevenLabs TTS] Complete: {total_bytes} bytes in {chunk_count} chunks, {elapsed:.2f}s")

        except Exception as exc:
            logger.error(f"[ElevenLabs TTS] Error during synthesis: {exc}", exc_info=True)
            raise


__all__ = ["sanitize_for_tts", "DeepgramTTSAdapter", "ElevenLabsTTSAdapter"]
