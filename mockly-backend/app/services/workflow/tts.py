"""
Deepgram streaming helpers used by the workflow endpoints.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import AsyncIterator, Iterable

from deepgram.core.events import EventType

from .clients import deepgram_client as dg
from .config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_SAMPLE_RATE,
    DEEPGRAM_STREAM_ENCODING,
    DEEPGRAM_TTS_VOICE,
)
from .speech import sanitize_for_tts
from .config import TTS_LIVE_JSON_PATH
from .captions import LiveTTSCapture


async def _send_chunks_via_ws(ws, sentences, capture: LiveTTSCapture | None = None) -> None:
    """
    Send sanitized Speak messages over the Deepgram websocket, flushing
    periodically to keep latency low.
    """
    try:
        FLUSH_CHARS = 220
        FLUSH_MS = 650
        last_flush = time.perf_counter()
        pending_chars = 0

        if hasattr(sentences, "__aiter__"):
            async for sentence in sentences:  # type: ignore[attr-defined]
                pending_chars = _send_sentence(ws, sentence, pending_chars, capture)
                last_flush, pending_chars = _maybe_flush(
                    ws, pending_chars, last_flush, FLUSH_CHARS, FLUSH_MS, capture
                )
                await asyncio.sleep(0)
        else:
            for sentence in sentences:  # type: ignore
                pending_chars = _send_sentence(ws, sentence, pending_chars, capture)
                last_flush, pending_chars = _maybe_flush(
                    ws, pending_chars, last_flush, FLUSH_CHARS, FLUSH_MS, capture
                )
                await asyncio.sleep(0)
    finally:
        with contextlib.suppress(Exception):
            ws.send_text(json.dumps({"type": "Flush"}))
            if capture:
                capture.flush()
        with contextlib.suppress(Exception):
            ws.send_text(json.dumps({"type": "Close"}))
        if capture:
            capture.close()


def _send_sentence(ws, sentence, pending_chars: int, capture: LiveTTSCapture | None = None) -> int:
    clean = sanitize_for_tts(str(sentence)).strip()
    if not clean:
        return pending_chars
    ws.send_text(json.dumps({"type": "Speak", "text": clean}))
    logging.info("[Deepgram WS] SENT Speak: %r", clean[:120])
    if capture:
        capture.speak(clean)
    return pending_chars + len(clean)


def _maybe_flush(
    ws,
    pending_chars: int,
    last_flush: float,
    flush_chars: int,
    flush_ms: int,
    capture: LiveTTSCapture | None = None,
) -> tuple[float, int]:
    now = time.perf_counter()
    if pending_chars >= flush_chars or (now - last_flush) * 1000.0 >= flush_ms:
        ws.send_text(json.dumps({"type": "Flush"}))
        logging.info("[Deepgram WS] SENT Flush")
        if capture:
            capture.flush()
        return now, 0
    return last_flush, pending_chars


def _pcm_duration_ms(nbytes: int, sample_rate: int) -> float:
    # linear16, 1 channel -> 2 bytes per sample
    return (nbytes / (2.0 * max(sample_rate, 1))) * 1000.0


async def stream_deepgram_tts(sentences) -> AsyncIterator[bytes]:
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    closed = {"flag": False}
    saw_audio = {"flag": False}
    capture: LiveTTSCapture | None = None
    if TTS_LIVE_JSON_PATH:
        try:
            capture = LiveTTSCapture(
                TTS_LIVE_JSON_PATH,
                sample_rate=DEEPGRAM_SAMPLE_RATE,
                encoding=str(DEEPGRAM_STREAM_ENCODING),
                voice=str(DEEPGRAM_TTS_VOICE),
            )
        except Exception:
            capture = None

    def on_message(msg):
        if isinstance(msg, (bytes, bytearray)):
            saw_audio["flag"] = True
            frame = bytes(msg)
            queue.put_nowait(frame)
            return
        mtype = getattr(msg, "type", None) or getattr(msg, "_type", None)
        data = getattr(msg, "data", None)
        if str(mtype).lower() == "audio" and isinstance(data, (bytes, bytearray)):
            saw_audio["flag"] = True
            frame = bytes(data)
            queue.put_nowait(frame)
            return
        logging.info("[Deepgram WS] non-audio: %r", msg)

    with dg.speak.v1.connect(
        model=DEEPGRAM_TTS_VOICE,
        encoding=DEEPGRAM_STREAM_ENCODING,
        sample_rate=DEEPGRAM_SAMPLE_RATE,
    ) as ws:
        ws.on(EventType.OPEN, lambda _: logging.info("[Deepgram WS] OPEN"))
        ws.on(EventType.MESSAGE, on_message)
        ws.on(
            EventType.CLOSE,
            lambda _: (closed.update({"flag": True}), logging.info("[Deepgram WS] CLOSE")),
        )
        ws.on(EventType.ERROR, lambda exc: logging.error("[Deepgram WS] ERROR: %s", exc))
        ws.start_listening()

        send_task = asyncio.create_task(_send_chunks_via_ws(ws, sentences, capture))

        last_audio = time.perf_counter()
        total = 0
        while True:
            try:
                frame = await asyncio.wait_for(queue.get(), timeout=0.8)
                total += len(frame)
                if capture and str(DEEPGRAM_STREAM_ENCODING).lower() == "linear16":
                    capture.audio(len(frame), _pcm_duration_ms(total, DEEPGRAM_SAMPLE_RATE))
                if total // 32768 != (total - len(frame)) // 32768:
                    logging.info("[Deepgram WS] audio %.1f KiB", total / 1024)
                yield frame
                last_audio = time.perf_counter()
            except asyncio.TimeoutError:
                if closed["flag"] and (time.perf_counter() - last_audio) > 0.8:
                    break

        if not send_task.done():
            send_task.cancel()
            with contextlib.suppress(Exception):
                await send_task

    if not saw_audio["flag"]:
        logging.warning("[Deepgram WS] no audio frames were received")


async def stream_deepgram_tts_raw(sentences: Iterable[str]) -> AsyncIterator[bytes]:
    try:
        import websockets  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency at runtime
        raise RuntimeError(
            "Missing dependency 'websockets'. Install with: pip install websockets"
        ) from exc

    from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK  # type: ignore

    url = (
        "wss://api.beta.deepgram.com/v1/speak?"
        f"model={DEEPGRAM_TTS_VOICE}&encoding={DEEPGRAM_STREAM_ENCODING}&sample_rate={DEEPGRAM_SAMPLE_RATE}"
    )
    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]

    try:
        connect_ctx = websockets.connect(url, extra_headers=headers, max_size=None)  # type: ignore[arg-type]
    except TypeError as exc:
        raise RuntimeError(
            "Incompatible 'websockets' package: missing support for extra_headers. "
            "Upgrade with: pip install -U websockets (>=12)."
        ) from exc

    capture: LiveTTSCapture | None = None
    if TTS_LIVE_JSON_PATH:
        try:
            capture = LiveTTSCapture(
                TTS_LIVE_JSON_PATH,
                sample_rate=DEEPGRAM_SAMPLE_RATE,
                encoding=str(DEEPGRAM_STREAM_ENCODING),
                voice=str(DEEPGRAM_TTS_VOICE),
            )
        except Exception:
            capture = None

    async with connect_ctx as ws:  # type: ignore
        async def sender() -> None:
            FLUSH_CHARS = 220
            FLUSH_MS = 650
            last_flush = time.perf_counter()
            pending_chars = 0
            try:
                if hasattr(sentences, "__aiter__"):
                    async for sentence in sentences:  # type: ignore[attr-defined]
                        pending_chars = _send_sentence(ws, sentence, pending_chars, capture)
                        last_flush, pending_chars = _maybe_flush(
                            ws, pending_chars, last_flush, FLUSH_CHARS, FLUSH_MS, capture
                        )
                        await asyncio.sleep(0)
                else:
                    for sentence in sentences:  # type: ignore
                        pending_chars = _send_sentence(ws, sentence, pending_chars, capture)
                        last_flush, pending_chars = _maybe_flush(
                            ws, pending_chars, last_flush, FLUSH_CHARS, FLUSH_MS, capture
                        )
                        await asyncio.sleep(0)
            except Exception:
                pass

        send_task = asyncio.create_task(sender())

        last_audio = time.perf_counter()
        total = 0
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.2)
                except asyncio.TimeoutError:
                    if send_task.done() and (time.perf_counter() - last_audio) > 1.0:
                        break
                    continue

                if isinstance(msg, (bytes, bytearray)):
                    last_audio = time.perf_counter()
                    frame = bytes(msg)
                    total += len(frame)
                    if capture and str(DEEPGRAM_STREAM_ENCODING).lower() == "linear16":
                        capture.audio(len(frame), _pcm_duration_ms(total, DEEPGRAM_SAMPLE_RATE))
                    yield frame
                    continue

                logging.info("[Deepgram WS raw] text: %s", msg)
        except ConnectionClosedOK:
            logging.info("[Deepgram WS raw] connection closed normally")
        except ConnectionClosedError as exc:
            logging.warning("[Deepgram WS raw] connection closed with error: %s", exc)
        finally:
            with contextlib.suppress(Exception):
                await ws.send(json.dumps({"type": "Flush"}))
                if capture:
                    capture.flush()
            with contextlib.suppress(Exception):
                await ws.send(json.dumps({"type": "Close"}))
            if capture:
                capture.close()
            with contextlib.suppress(Exception):
                await ws.close()
            if not send_task.done():
                send_task.cancel()
                with contextlib.suppress(Exception):
                    await send_task


__all__ = ["stream_deepgram_tts", "stream_deepgram_tts_raw"]
