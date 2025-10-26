"""
TTS streaming helpers used by the workflow endpoints.
Now using ElevenLabs for text-to-speech generation.
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
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL,
    ELEVENLABS_OUTPUT_FORMAT,
)
from .speech import sanitize_for_tts
from .config import (
    TTS_LIVE_JSON_PATH,
    LIVE_TRANSCRIPTION_PATH,
    LIVE_TRANSCRIPTION_UPDATE_INTERVAL,
)
from .captions import LiveTTSCapture
from .live_transcription import LiveTranscriptionWriter


async def _send_chunks_via_ws(
    ws,
    sentences,
    capture: LiveTTSCapture | None = None,
    transcription: LiveTranscriptionWriter | None = None,
) -> None:
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
                pending_chars = _send_sentence(ws, sentence, pending_chars, capture, transcription)
                last_flush, pending_chars = _maybe_flush(
                    ws, pending_chars, last_flush, FLUSH_CHARS, FLUSH_MS, capture
                )
                await asyncio.sleep(0)
        else:
            for sentence in sentences:  # type: ignore
                pending_chars = _send_sentence(ws, sentence, pending_chars, capture, transcription)
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
        if transcription:
            with contextlib.suppress(Exception):
                await transcription.finalize()
            transcription.close()


def _send_sentence(
    ws,
    sentence,
    pending_chars: int,
    capture: LiveTTSCapture | None = None,
    transcription: LiveTranscriptionWriter | None = None,
) -> int:
    """Send sentence via Deepgram SDK websocket (uses send_text method)"""
    clean = sanitize_for_tts(str(sentence)).strip()
    if not clean:
        return pending_chars
    ws.send_text(json.dumps({"type": "Speak", "text": clean}))
    logging.info("[Deepgram WS] SENT Speak: %r", clean[:120])
    if capture:
        capture.speak(clean)
    if transcription:
        transcription.add_text_chunk(clean)
    return pending_chars + len(clean)


async def _send_sentence_raw(
    ws,
    sentence,
    pending_chars: int,
    capture: LiveTTSCapture | None = None,
    transcription: LiveTranscriptionWriter | None = None,
) -> int:
    """Send sentence via raw websockets library (uses send method)"""
    send_start = time.perf_counter()
    clean = sanitize_for_tts(str(sentence)).strip()
    if not clean:
        logging.info("[Deepgram WS raw] SKIP empty after sanitize: %r", sentence[:80])
        return pending_chars
    await ws.send(json.dumps({"type": "Speak", "text": clean}))
    send_time = (time.perf_counter() - send_start) * 1000
    logging.info("[Deepgram WS raw] SENT Speak (%d chars in %.1fms): %r", len(clean), send_time, clean[:120])
    if capture:
        capture.speak(clean)
    if transcription:
        transcription.add_text_chunk(clean)
    return pending_chars + len(clean)


def _maybe_flush(
    ws,
    pending_chars: int,
    last_flush: float,
    flush_chars: int,
    flush_ms: int,
    capture: LiveTTSCapture | None = None,
) -> tuple[float, int]:
    """Maybe flush Deepgram SDK websocket (uses send_text method)"""
    now = time.perf_counter()
    if pending_chars >= flush_chars or (now - last_flush) * 1000.0 >= flush_ms:
        ws.send_text(json.dumps({"type": "Flush"}))
        logging.info("[Deepgram WS] SENT Flush")
        if capture:
            capture.flush()
        return now, 0
    return last_flush, pending_chars


async def _maybe_flush_raw(
    ws,
    pending_chars: int,
    last_flush: float,
    flush_chars: int,
    flush_ms: int,
    capture: LiveTTSCapture | None = None,
) -> tuple[float, int]:
    """Maybe flush raw websockets (uses send method)"""
    now = time.perf_counter()
    if pending_chars >= flush_chars or (now - last_flush) * 1000.0 >= flush_ms:
        await ws.send(json.dumps({"type": "Flush"}))
        logging.info("[Deepgram WS raw] SENT Flush")
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
    transcription: LiveTranscriptionWriter | None = None
    
    # Initialize caption capture if configured
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
    
    # Initialize live transcription for word-level timestamps (needed for lip sync)
    # Re-transcribing TTS audio gives us precise word timing from Deepgram STT
    transcription = None
    if LIVE_TRANSCRIPTION_PATH:
        try:
            transcription = LiveTranscriptionWriter(
                LIVE_TRANSCRIPTION_PATH,
                sample_rate=DEEPGRAM_SAMPLE_RATE,
                encoding=str(DEEPGRAM_STREAM_ENCODING),
                update_interval_seconds=LIVE_TRANSCRIPTION_UPDATE_INTERVAL,
            )
            logging.info(f"[Deepgram TTS] ✅ Live transcription ENABLED: path={LIVE_TRANSCRIPTION_PATH}, encoding={DEEPGRAM_STREAM_ENCODING}")
        except Exception as exc:
            logging.error(f"[Deepgram TTS] ❌ Failed to init transcription: {exc}", exc_info=True)
            transcription = None
    else:
        logging.warning("[Deepgram TTS] Live transcription DISABLED: LIVE_TRANSCRIPTION_PATH not set")

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

        send_task = asyncio.create_task(_send_chunks_via_ws(ws, sentences, capture, transcription))

        last_audio = time.perf_counter()
        total = 0
        while True:
            try:
                frame = await asyncio.wait_for(queue.get(), timeout=10.0)
                total += len(frame)
                duration_ms = _pcm_duration_ms(total, DEEPGRAM_SAMPLE_RATE)
                
                if capture and str(DEEPGRAM_STREAM_ENCODING).lower() == "linear16":
                    capture.audio(len(frame), duration_ms)
                
                # Add audio to transcription buffer
                if transcription and str(DEEPGRAM_STREAM_ENCODING).lower() == "linear16":
                    transcription.add_audio_chunk(frame, _pcm_duration_ms(len(frame), DEEPGRAM_SAMPLE_RATE))
                    # Periodically trigger transcription update
                    await transcription.maybe_update()
                
                if total // 32768 != (total - len(frame)) // 32768:
                    logging.info("[Deepgram WS] audio %.1f KiB", total / 1024)
                yield frame
                last_audio = time.perf_counter()
            except asyncio.TimeoutError:
                # Only break if connection is closed AND no audio for 10 seconds
                if closed["flag"] and (time.perf_counter() - last_audio) > 10.0:
                    logging.info("[Deepgram WS] Stream ended after 10s idle")
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
    
    logging.info(f"[Deepgram TTS raw] Connecting to {url[:80]}...")
    
    # Build headers dict for websockets.connect()
    # Use additional_headers instead of extra_headers for better compatibility
    headers_dict = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    try:
        # Try with additional_headers first (websockets 12+)
        connect_ctx = websockets.connect(
            url, 
            additional_headers=headers_dict,
            max_size=None
        )  # type: ignore[call-arg]
    except TypeError:
        try:
            # Fallback to extra_headers for older versions
            logging.info("[Deepgram TTS raw] Falling back to extra_headers parameter")
            connect_ctx = websockets.connect(
                url,
                extra_headers=headers_dict,
                max_size=None
            )  # type: ignore[call-arg]
        except TypeError as exc:
            raise RuntimeError(
                "Incompatible 'websockets' package. "
                "Upgrade with: pip install -U 'websockets>=12.0'"
            ) from exc

    capture: LiveTTSCapture | None = None
    transcription: LiveTranscriptionWriter | None = None
    
    # Initialize caption capture if configured
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
    
    # Initialize live transcription for word-level timestamps (needed for lip sync)
    # Re-transcribing TTS audio gives us precise word timing from Deepgram STT
    transcription = None
    if LIVE_TRANSCRIPTION_PATH:
        try:
            transcription = LiveTranscriptionWriter(
                LIVE_TRANSCRIPTION_PATH,
                sample_rate=DEEPGRAM_SAMPLE_RATE,
                encoding=str(DEEPGRAM_STREAM_ENCODING),
                update_interval_seconds=LIVE_TRANSCRIPTION_UPDATE_INTERVAL,
            )
            logging.info(f"[Deepgram TTS raw] ✅ Live transcription ENABLED: path={LIVE_TRANSCRIPTION_PATH}, encoding={DEEPGRAM_STREAM_ENCODING}")
        except Exception as exc:
            logging.error(f"[Deepgram TTS raw] ❌ Failed to init transcription: {exc}", exc_info=True)
            transcription = None
    else:
        logging.warning("[Deepgram TTS raw] Live transcription DISABLED: LIVE_TRANSCRIPTION_PATH not set")

    async with connect_ctx as ws:  # type: ignore
        logging.info("[Deepgram TTS raw] WebSocket connected successfully")
        
        async def sender() -> None:
            FLUSH_CHARS = 220
            FLUSH_MS = 650
            last_flush = time.perf_counter()
            pending_chars = 0
            sentence_count = 0
            try:
                if hasattr(sentences, "__aiter__"):
                    async for sentence in sentences:  # type: ignore[attr-defined]
                        sentence_count += 1
                        logging.info(f"[Deepgram TTS raw] Processing sentence {sentence_count}: {sentence[:80]}...")
                        pending_chars = await _send_sentence_raw(ws, sentence, pending_chars, capture, transcription)
                        last_flush, pending_chars = await _maybe_flush_raw(
                            ws, pending_chars, last_flush, FLUSH_CHARS, FLUSH_MS, capture
                        )
                        await asyncio.sleep(0)
                else:
                    for sentence in sentences:  # type: ignore
                        sentence_count += 1
                        logging.info(f"[Deepgram TTS raw] Processing sentence {sentence_count}: {sentence[:80]}...")
                        pending_chars = await _send_sentence_raw(ws, sentence, pending_chars, capture, transcription)
                        last_flush, pending_chars = await _maybe_flush_raw(
                            ws, pending_chars, last_flush, FLUSH_CHARS, FLUSH_MS, capture
                        )
                        await asyncio.sleep(0)
                
                # Final flush to ensure all text is sent
                if pending_chars > 0:
                    logging.info(f"[Deepgram TTS raw] Final flush with {pending_chars} pending chars")
                    await ws.send(json.dumps({"type": "Flush"}))
                    if capture:
                        capture.flush()
                
                logging.info(f"[Deepgram TTS raw] Sent {sentence_count} sentences to Deepgram")
                if sentence_count == 0:
                    logging.warning("[Deepgram TTS raw] No sentences to send!")
                else:
                    logging.info(f"[Deepgram TTS raw] Sender completed successfully")
            except Exception as exc:
                logging.error(f"[Deepgram TTS raw] Error in sender: {exc}", exc_info=True)
            finally:
                logging.info("[Deepgram TTS raw] Sender task finished")

        send_task = asyncio.create_task(sender())

        last_audio = time.perf_counter()
        total = 0
        audio_chunks_received = 0
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Log status during timeout
                    idle_time = time.perf_counter() - last_audio
                    logging.info(f"[Deepgram TTS raw] Timeout: sender_done={send_task.done()}, idle={idle_time:.1f}s, chunks={audio_chunks_received}, bytes={total}")
                    
                    # Only break if sender is done AND no audio for 15 seconds
                    if send_task.done() and idle_time > 15.0:
                        logging.info(f"[Deepgram TTS raw] Stream complete after {idle_time:.1f}s idle, total audio: {total} bytes")
                        break
                    # Still waiting for more audio, continue
                    continue

                if isinstance(msg, (bytes, bytearray)):
                    now = time.perf_counter()
                    gap_since_last = now - last_audio
                    last_audio = now
                    
                    frame = bytes(msg)
                    total += len(frame)
                    audio_chunks_received += 1
                    duration_ms = _pcm_duration_ms(total, DEEPGRAM_SAMPLE_RATE)
                    
                    # Log gaps that could cause playback issues
                    if gap_since_last > 1.0 and audio_chunks_received > 1:
                        logging.warning(f"[Deepgram TTS raw] Large gap detected: {gap_since_last:.2f}s since last audio chunk")
                    
                    if audio_chunks_received % 10 == 0:
                        logging.info(f"[Deepgram TTS raw] Received {audio_chunks_received} audio chunks, {total} bytes total, last gap: {gap_since_last:.3f}s")
                    
                    if capture and str(DEEPGRAM_STREAM_ENCODING).lower() == "linear16":
                        capture.audio(len(frame), duration_ms)
                    
                    # Add audio to transcription buffer
                    if transcription and str(DEEPGRAM_STREAM_ENCODING).lower() == "linear16":
                        transcription.add_audio_chunk(frame, _pcm_duration_ms(len(frame), DEEPGRAM_SAMPLE_RATE))
                        # Periodically trigger transcription update
                        await transcription.maybe_update()
                    elif audio_chunks_received == 1:  # Log once at start
                        if not transcription:
                            logging.warning("[Deepgram TTS raw] Transcription not initialized - check LIVE_TRANSCRIPTION_PATH")
                        elif str(DEEPGRAM_STREAM_ENCODING).lower() != "linear16":
                            logging.warning(f"[Deepgram TTS raw] Wrong encoding for transcription: {DEEPGRAM_STREAM_ENCODING} (need linear16)")
                    
                    yield frame
                    continue

                logging.info("[Deepgram WS raw] text message: %s", msg)
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
            if transcription:
                with contextlib.suppress(Exception):
                    await transcription.finalize()
                transcription.close()
            with contextlib.suppress(Exception):
                await ws.close()
            if not send_task.done():
                send_task.cancel()
                with contextlib.suppress(Exception):
                    await send_task


async def stream_elevenlabs_tts(sentences: Iterable[str]) -> AsyncIterator[bytes]:
    """
    Stream TTS audio from ElevenLabs API.
    
    Takes an iterable of text sentences and yields PCM audio bytes suitable
    for the talking head. Uses the websocket streaming API for low latency.
    """
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import Voice, VoiceSettings
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'elevenlabs'. Install with: pip install elevenlabs"
        ) from exc
    
    logging.info(f"[ElevenLabs TTS] Initializing with voice={ELEVENLABS_VOICE_ID}, model={ELEVENLABS_MODEL}")
    
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    
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
        logging.warning("[ElevenLabs TTS] No sentences to synthesize")
        return
    
    full_text = " ".join(sentence_buffer)
    logging.info(f"[ElevenLabs TTS] Synthesizing {len(full_text)} characters across {len(sentence_buffer)} sentences")
    logging.info(f"[ElevenLabs TTS] Text preview: {full_text[:200]}...")
    
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
                    logging.info(f"[ElevenLabs TTS] First audio chunk after {first_chunk_time*1000:.1f}ms")
                yield chunk
                # Allow other async tasks to run
                await asyncio.sleep(0)
        
        elapsed = time.perf_counter() - start_time
        logging.info(f"[ElevenLabs TTS] Complete: {total_bytes} bytes in {chunk_count} chunks, {elapsed:.2f}s")
        
    except Exception as exc:
        logging.error(f"[ElevenLabs TTS] Error during synthesis: {exc}", exc_info=True)
        raise


__all__ = ["stream_deepgram_tts", "stream_deepgram_tts_raw", "stream_elevenlabs_tts"]
