from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse


router = APIRouter(prefix="/api", tags=["audio"])


AUDIO_PATH = Path(__file__).resolve().parent.parent / "assets" / "audio.mp3"
CHUNK_SIZE = 1024 * 64  # 64 KiB chunks keep latency low without spamming the event loop.
RANGE_PATTERN = re.compile(r"bytes=(\d+)-(\d*)")


def _iter_file(start: int = 0, end: Optional[int] = None) -> Iterator[bytes]:
    with AUDIO_PATH.open("rb") as stream:
        stream.seek(start)
        remaining = None if end is None else (end - start + 1)

        while True:
            read_size = CHUNK_SIZE if remaining is None else min(CHUNK_SIZE, remaining)
            chunk = stream.read(read_size)
            if not chunk:
                break
            yield chunk
            if remaining is not None:
                remaining -= len(chunk)
                if remaining <= 0:
                    break


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    match = RANGE_PATTERN.match(range_header)
    if not match:
        return 0, file_size - 1

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else file_size - 1

    if start >= file_size:
        raise HTTPException(
            status_code=416,
            detail="Requested range not satisfiable.",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    end = min(end, file_size - 1)
    if start > end:
        raise HTTPException(
            status_code=416,
            detail="Invalid range requested.",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    return start, end


@router.get("/audio/stream")
async def stream_audio(request: Request):
    """
    Streams the demo audio track with basic Range request support so the frontend
    can progressively download or seek within the file.
    """
    if not AUDIO_PATH.exists():
        raise HTTPException(status_code=404, detail="Audio asset is not available.")

    file_size = AUDIO_PATH.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        start, end = _parse_range(range_header, file_size)
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
        }
        return StreamingResponse(
            _iter_file(start, end),
            status_code=206,
            media_type="audio/mpeg",
            headers=headers,
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
    }
    return StreamingResponse(
        _iter_file(),
        media_type="audio/mpeg",
        headers=headers,
    )
