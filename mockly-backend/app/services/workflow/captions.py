from __future__ import annotations

import json
import os
import threading
import time
from typing import Any


class LiveTTSCapture:
    """
    Append line-delimited JSON (NDJSON) events describing TTS activity.

    Events:
      - {event: "session", started_at_ms, sample_rate, encoding, voice}
      - {event: "speak", at_ms, index, text}
      - {event: "flush", at_ms}
      - {event: "audio", at_ms, bytes, elapsed_ms}
      - {event: "close", at_ms, elapsed_ms}
    """

    def __init__(self, path: str, *, sample_rate: int, encoding: str, voice: str):
        self.path = path
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.voice = voice
        self._lock = threading.Lock()
        self._t0 = time.perf_counter()
        self._elapsed_ms = 0.0
        self._index = 0
        # Ensure directory exists if a nested path was given
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        except Exception:
            pass
        self._write({
            "event": "session",
            "started_at_ms": 0,
            "sample_rate": sample_rate,
            "encoding": encoding,
            "voice": voice,
        })

    def _now_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0

    def _write(self, obj: dict[str, Any]) -> None:
        try:
            line = json.dumps(obj, ensure_ascii=False)
        except Exception:
            # Fallback to string repr if non-serializable
            line = json.dumps({"event": "error", "detail": str(obj)})
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def speak(self, text: str) -> None:
        self._write({
            "event": "speak",
            "at_ms": round(self._now_ms(), 3),
            "index": self._index,
            "text": text,
        })
        self._index += 1

    def flush(self) -> None:
        self._write({"event": "flush", "at_ms": round(self._now_ms(), 3)})

    def audio(self, bytes_len: int, elapsed_ms: float) -> None:
        self._elapsed_ms = elapsed_ms
        self._write({
            "event": "audio",
            "at_ms": round(self._now_ms(), 3),
            "bytes": int(bytes_len),
            "elapsed_ms": round(elapsed_ms, 3),
        })

    def close(self) -> None:
        self._write({
            "event": "close",
            "at_ms": round(self._now_ms(), 3),
            "elapsed_ms": round(self._elapsed_ms, 3),
        })


__all__ = ["LiveTTSCapture"]

