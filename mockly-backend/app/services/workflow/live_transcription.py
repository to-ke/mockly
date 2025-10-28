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
        min_audio_bytes: int = 192000,  # ~2 seconds at 48kHz 16-bit (was 96000)
    ):
        """
        Initialize the live transcription writer.
        
        Args:
            output_path: Path to the JSON file to write
            sample_rate: Audio sample rate (Hz)
            encoding: Audio encoding format
            update_interval_seconds: How often to update the JSON file
            min_audio_bytes: Minimum audio bytes before attempting transcription
                           (192000 bytes = ~2 seconds at 48kHz 16-bit)
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
            before_size = self._audio_buffer.tell()
            self._audio_buffer.write(audio_bytes)
            after_size = self._audio_buffer.tell()
            self._total_audio_duration_ms += duration_ms
            
            # Log periodically to track buffer growth
            if after_size // 50000 != before_size // 50000:  # Log every ~50KB
                logging.debug(
                    f"[LiveTranscription] Buffer: {after_size} bytes "
                    f"({self._total_audio_duration_ms/1000:.1f}s total audio)"
                )

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
                # Log status periodically for debugging
                if buffer_size > 0 and time_since_last >= self.update_interval:
                    logging.debug(
                        f"[LiveTranscription] Waiting for more audio: "
                        f"{buffer_size} bytes (need {self.min_audio_bytes})"
                    )
                return
            
            # Extract audio for transcription
            audio_data = self._audio_buffer.getvalue()
            self._audio_buffer = BytesIO()  # Reset buffer
            self._last_update_time = now
            
            logging.info(
                f"[LiveTranscription] Triggering transcription: "
                f"{len(audio_data)} bytes, {time_since_last:.1f}s since last update"
            )
        
        # Transcribe outside the lock
        try:
            await self._transcribe_and_update(audio_data)
        except Exception as exc:
            logging.error(f"[LiveTranscription] Update failed: {exc}", exc_info=True)

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
        if not audio_data or len(audio_data) == 0:
            logging.warning("[LiveTranscription] Empty audio data, skipping transcription")
            return []
        
        # Log audio size for debugging
        logging.info(f"[LiveTranscription] Transcribing {len(audio_data)} bytes of audio")
        
        # For raw PCM audio, use query parameters for encoding
        # This is the correct way to send raw audio to Deepgram
        # NOTE: All params must be strings for proper URL encoding
        if self.encoding.lower() in ("linear16", "pcm"):
            content_type = "audio/raw"
            params = {
                "model": DEEPGRAM_STT_MODEL,
                "punctuate": "true",  # String, not boolean
                "utterances": "false",
                "smart_format": "true",
                "encoding": "linear16",
                "sample_rate": str(self.sample_rate),  # Convert to string
                "channels": "1",
            }
        else:
            content_type = "audio/wav"
            params = {
                "model": DEEPGRAM_STT_MODEL,
                "punctuate": "true",
                "utterances": "false",
                "smart_format": "true",
            }
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": content_type,
        }
        
        url = "https://api.deepgram.com/v1/listen"
        
        # Log the full request for debugging
        logging.info(f"[LiveTranscription] Request URL: {url}")
        logging.info(f"[LiveTranscription] Params: {params}")
        logging.info(f"[LiveTranscription] Content-Type: {content_type}")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    params=params,
                    headers=headers,
                    content=audio_data,
                )
                
                # Log response status for debugging
                logging.info(f"[LiveTranscription] Deepgram response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text
                    logging.error(f"[LiveTranscription] Deepgram API error {response.status_code}: {error_text}")
                    return []
                
                data = response.json()
                
                # DEBUG: Save response to file for inspection
                try:
                    with open("deepgram_response_debug.json", "w") as f:
                        json.dump(data, f, indent=2)
                    logging.info("[LiveTranscription] Saved Deepgram response to deepgram_response_debug.json")
                except Exception:
                    pass
                    
        except httpx.HTTPStatusError as exc:
            logging.error(f"[LiveTranscription] HTTP error {exc.response.status_code}: {exc.response.text}")
            return []
        except Exception as exc:
            logging.error(f"[LiveTranscription] Deepgram API error: {exc}", exc_info=True)
            return []
        
        # Extract word timestamps
        try:
            # Log the full response structure for debugging
            results = data.get("results", {})
            channels = results.get("channels", [])
            
            if not channels:
                logging.error("[LiveTranscription] No channels in Deepgram response")
                logging.error(f"[LiveTranscription] Full response: {json.dumps(data, indent=2)}")
                return []
            
            alternatives = channels[0].get("alternatives", [])
            if not alternatives:
                logging.error("[LiveTranscription] No alternatives in Deepgram response")
                logging.error(f"[LiveTranscription] Full response: {json.dumps(data, indent=2)}")
                return []
            
            # Log the transcript to see if we got anything
            transcript = alternatives[0].get("transcript", "")
            logging.info(f"[LiveTranscription] Transcript received: '{transcript}'")
            
            if not transcript or transcript.strip() == "":
                logging.warning("[LiveTranscription] Empty transcript - audio may be silent or too short")
                logging.info(f"[LiveTranscription] Audio was {len(audio_data)} bytes = {len(audio_data)/96000:.2f} seconds at 48kHz")
                return []
            
            words_data = alternatives[0].get("words", [])
            
            if not words_data:
                logging.warning("[LiveTranscription] No words in Deepgram response despite having transcript")
                logging.warning(f"[LiveTranscription] Transcript was: '{transcript}'")
                logging.debug(f"[LiveTranscription] Full response: {json.dumps(data, indent=2)}")
                return []
            
            word_list = []
            for word_obj in words_data:
                word_list.append({
                    "word": word_obj.get("word", ""),
                    "start_time": round(word_obj.get("start", 0.0), 3),
                    "end_time": round(word_obj.get("end", 0.0), 3),
                })
            
            logging.info(f"[LiveTranscription] Extracted {len(word_list)} words")
            return word_list
            
        except Exception as exc:
            logging.error(f"[LiveTranscription] Failed to parse words: {exc}", exc_info=True)
            logging.debug(f"[LiveTranscription] Response data: {data}")
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

