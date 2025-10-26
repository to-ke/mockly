"""
Live transcription system for TTS-generated audio.

Provides real-time word-level timestamps for frontend consumption by
transcribing generated audio chunks and maintaining an updated JSON file.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from .config import DEEPGRAM_API_KEY, DEEPGRAM_STT_MODEL


class LiveTranscriptionWriter:
    """
    Manages live transcription data with word-level timestamps.
    
    Accumulates audio chunks, periodically transcribes them via Deepgram STT,
    and writes a JSON file with word timestamps that the frontend can poll.
    """

    def __init__(
        self,
        output_path: str,
        *,
        sample_rate: int = 48000,
        encoding: str = "linear16",
        update_interval_seconds: float = 2.0,
        min_audio_bytes: int = 96000,  # ~1 second at 48kHz 16-bit
    ):
        """
        Initialize the live transcription writer.
        
        Args:
            output_path: Path to the JSON file to write
            sample_rate: Audio sample rate (Hz)
            encoding: Audio encoding format
            update_interval_seconds: How often to update the JSON file
            min_audio_bytes: Minimum audio bytes before attempting transcription
        """
        self.output_path = Path(output_path)
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.update_interval = update_interval_seconds
        self.min_audio_bytes = min_audio_bytes
        
        # Thread-safe state
        self._lock = threading.Lock()
        self._audio_buffer = BytesIO()
        self._total_audio_duration_ms = 0.0
        self._all_words: list[dict[str, Any]] = []
        self._pending_text_chunks: list[str] = []
        
        # Timing
        self._last_update_time = 0.0
        self._session_start = time.perf_counter()
        
        # Background processing
        self._update_task: asyncio.Task | None = None
        self._should_stop = False
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize with empty transcription
        self._write_json_file([])
        
        logging.info(
            "[LiveTranscription] Initialized: output=%s, sample_rate=%d, "
            "update_interval=%.1fs",
            output_path,
            sample_rate,
            update_interval_seconds,
        )

    def add_audio_chunk(self, audio_bytes: bytes, duration_ms: float) -> None:
        """
        Add a chunk of generated audio to the buffer.
        
        Args:
            audio_bytes: Raw audio bytes (PCM 16-bit)
            duration_ms: Duration of this audio chunk in milliseconds
        """
        with self._lock:
            self._audio_buffer.write(audio_bytes)
            self._total_audio_duration_ms += duration_ms

    def add_text_chunk(self, text: str) -> None:
        """
        Add a text chunk that was sent to TTS (for reference).
        
        Args:
            text: The text being converted to speech
        """
        with self._lock:
            self._pending_text_chunks.append(text)

    async def maybe_update(self) -> None:
        """
        Check if it's time to update the transcription file.
        
        This should be called periodically from the main async loop.
        Will trigger transcription if enough time has passed and sufficient
        audio has been accumulated.
        """
        now = time.perf_counter()
        
        # Check if we should update
        with self._lock:
            time_since_last = now - self._last_update_time
            buffer_size = self._audio_buffer.tell()
            
            should_update = (
                time_since_last >= self.update_interval
                and buffer_size >= self.min_audio_bytes
            )
            
            if not should_update:
                return
            
            # Extract audio for transcription
            audio_data = self._audio_buffer.getvalue()
            self._audio_buffer = BytesIO()  # Reset buffer
            self._last_update_time = now
        
        # Transcribe outside the lock
        try:
            await self._transcribe_and_update(audio_data)
        except Exception as exc:
            logging.error("[LiveTranscription] Update failed: %s", exc, exc_info=True)

    async def _transcribe_and_update(self, audio_data: bytes) -> None:
        """
        Transcribe audio data and update the JSON file.
        
        Args:
            audio_data: Raw audio bytes to transcribe
        """
        if not audio_data:
            return
        
        # Get word-level timestamps from Deepgram
        word_timestamps = await self._get_word_timestamps(audio_data)
        
        if not word_timestamps:
            logging.warning("[LiveTranscription] No words received from transcription")
            return
        
        # Merge with existing words
        with self._lock:
            self._all_words.extend(word_timestamps)
            
            # Write updated JSON
            self._write_json_file(self._all_words)
        
        logging.info(
            "[LiveTranscription] Updated with %d new words (total: %d)",
            len(word_timestamps),
            len(self._all_words),
        )

    async def _get_word_timestamps(self, audio_data: bytes) -> list[dict[str, Any]]:
        """
        Transcribe audio and extract word-level timestamps.
        
        Args:
            audio_data: Raw PCM audio bytes
            
        Returns:
            List of word dictionaries with start_time, end_time, and word
        """
        # Determine content type based on encoding
        if self.encoding.lower() in ("linear16", "pcm"):
            content_type = f"audio/raw; encoding=signed-integer; bits=16; sample_rate={self.sample_rate}; channels=1"
        else:
            content_type = "audio/wav"  # Fallback
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": content_type,
        }
        
        # Request word-level timestamps
        params = {
            "model": DEEPGRAM_STT_MODEL,
            "punctuate": True,
            "utterances": False,  # We want words, not utterances
            "smart_format": True,
        }
        
        url = "https://api.deepgram.com/v1/listen"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    params=params,
                    headers=headers,
                    content=audio_data,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logging.error("[LiveTranscription] Deepgram API error: %s", exc)
            return []
        
        # Extract word timestamps
        try:
            words_data = (
                data.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("words", [])
            )
            
            word_list = []
            for word_obj in words_data:
                word_list.append({
                    "word": word_obj.get("word", ""),
                    "start_time": round(word_obj.get("start", 0.0), 3),
                    "end_time": round(word_obj.get("end", 0.0), 3),
                })
            
            return word_list
            
        except Exception as exc:
            logging.error("[LiveTranscription] Failed to parse words: %s", exc)
            logging.debug("[LiveTranscription] Response data: %s", data)
            return []

    def _write_json_file(self, words: list[dict[str, Any]]) -> None:
        """
        Write the transcription data to JSON file (thread-safe).
        
        Overwrites the entire file with the current transcription state.
        
        Args:
            words: List of word dictionaries
        """
        output_data = {
            "transcription": words,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "word_count": len(words),
        }
        
        try:
            # Write to temp file first, then atomic rename
            temp_path = self.output_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # Atomic replacement to avoid partial reads
            temp_path.replace(self.output_path)
            
        except Exception as exc:
            logging.error("[LiveTranscription] Failed to write JSON: %s", exc)

    async def finalize(self) -> None:
        """
        Finalize transcription by processing any remaining audio.
        
        Call this when the TTS stream is complete.
        """
        with self._lock:
            remaining_audio = self._audio_buffer.getvalue()
            self._audio_buffer = BytesIO()
        
        if remaining_audio:
            try:
                await self._transcribe_and_update(remaining_audio)
            except Exception as exc:
                logging.error("[LiveTranscription] Final update failed: %s", exc)
        
        logging.info("[LiveTranscription] Finalized with %d total words", len(self._all_words))

    def close(self) -> None:
        """Clean up resources."""
        self._should_stop = True
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()


__all__ = ["LiveTranscriptionWriter"]

