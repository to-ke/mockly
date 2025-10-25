# api.py — Streaming Claude (SSE) -> Streaming Deepgram TTS (WS)

from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import Response, StreamingResponse
import asyncio
import logging
from typing import AsyncIterator, Iterable
import re
import time
import contextlib
import json
from pathlib import Path
import base64
import httpx
import os

from anthropic import Anthropic
from deepgram import DeepgramClient
from deepgram.core.events import EventType
from fastapi.middleware.cors import CORSMiddleware


from config import (
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    DEEPGRAM_API_KEY, DEEPGRAM_TTS_VOICE,
    DEEPGRAM_STREAM_ENCODING, DEEPGRAM_SAMPLE_RATE,
    CORS_ALLOW_ORIGINS,
)

# Optional YAML support for loading questions by difficulty
try:
    import yaml as _yaml  # type: ignore
except Exception:  # pragma: no cover
    _yaml = None

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Local Voice/Text Assistant Streaming")

# CORS so FE can POST JSON and stream responses
_cors_origins = CORS_ALLOW_ORIGINS if CORS_ALLOW_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# ---------- SDK clients ----------
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
dg = DeepgramClient(api_key=DEEPGRAM_API_KEY)

# ---------- Helpers: Build per-request system prompt from question ----------
def _format_examples(examples) -> str:
    try:
        if not examples:
            return ""
        lines = []
        for ex in examples:
            if isinstance(ex, dict):
                name = ex.get("name") or ex.get("title") or "example"
                inp = ex.get("input")
                out = ex.get("output")
                expl = ex.get("explanation")
                seg = f"- {name}:\n  input: {inp}\n  output: {out}"
                if expl:
                    seg += f"\n  note: {expl}"
                lines.append(seg)
            else:
                lines.append(f"- {ex}")
        return "\n".join(lines)
    except Exception:
        return ""


def build_system_prompt_from_question(question: dict | None) -> str:
    # New interviewer system prompt with rating criteria and evaluation format.
    # Always construct a full hardcoded prompt; no dependency on env/config.
    if not isinstance(question, dict):
        question = {}

    title = (question.get("title") or "").strip()
    difficulty = (question.get("difficulty") or "").strip()
    statement = (question.get("statement") or question.get("prompt") or "").strip()
    input_fmt = (question.get("input_format") or "").strip()
    output_fmt = (question.get("output_format") or "").strip()
    examples = _format_examples(question.get("examples"))
    hints = question.get("hints") or []
    hints_list: list[str] = []
    if isinstance(hints, list):
        hints_list = [str(h).strip() for h in hints if str(h).strip()]
    else:
        if str(hints).strip():
            hints_list = [str(hints).strip()]

    # Limit to first two hints per the new rules
    limited_hints = hints_list[:2]
    limited_hints_text = "\n".join(f"- {h}" for h in limited_hints)

    # Build QUESTION_DETAILS block
    qd_lines: list[str] = []
    if title or difficulty:
        head = []
        if title:
            head.append(f"Title: {title}")
        if difficulty:
            head.append(f"Difficulty: {difficulty}")
        qd_lines.append(" ".join(head))
        qd_lines.append("")
    if statement:
        qd_lines.append("Problem Statement:")
        qd_lines.append(statement)
        qd_lines.append("")
    if input_fmt:
        qd_lines.append("Input Format:")
        qd_lines.append(input_fmt)
        qd_lines.append("")
    if output_fmt:
        qd_lines.append("Output Format:")
        qd_lines.append(output_fmt)
        qd_lines.append("")
    if examples:
        qd_lines.append("Examples:")
        qd_lines.append(examples)
        qd_lines.append("")
    if limited_hints_text:
        qd_lines.append("Hints (use at most two; ordered):")
        qd_lines.append(limited_hints_text)
        qd_lines.append("")

    question_details = "\n".join([ln for ln in qd_lines if ln is not None])

    parts = [
        "You will be acting as a technical interviewer conducting a coding interview with a candidate. "
        "You will present them with a LeetCode-style algorithmic problem and evaluate their performance.",
        "",
        "Here are the question details you should use:",
        "<question_details>",
        question_details,
        "</question_details>",
        "",
        "When I write BEGIN INTERVIEW, you will start the technical interview. "
        "All further input will be from the candidate attempting to solve the problem.",
        "",
        "Here are the important rules for conducting the interview:",
        "",
        "**Voice Output Rules (Important):**",
        "- Speak naturally and conversationally; avoid robotic or literal reading.",
        "- Do NOT vocalize formatting symbols like **, __, #, ##, <...>, </...>, backticks, or code fences.",
        "- Do not say phrases like 'star star' or 'pound pound'; omit formatting markers entirely.",
        "- When presenting structure, use plain sentences (e.g., 'Code Cleanliness score is 4 out of 5').",
        "- Do not read XML-like tags (e.g., <evaluation>) aloud; treat them as meta and exclude them from speech.",
        "",
        "**Presenting the Problem:**",
        "- Present the coding question in a language-agnostic way since the candidate can choose any programming language",
        "- Clearly state the problem, provide examples, and specify any constraints",
        "- Do not mention specific language syntax or data structures that are language-specific",
        "- Do not ask what programming language they want to use; stay language-agnostic unless they volunteer a preference",
        "",
        "**Giving Hints:**",
        "- You have exactly TWO hints available from the question details",
        "- Only provide a hint if the candidate is clearly stuck or explicitly asks for help",
        "- Give hints one at a time, not both at once",
        "- Keep track of how many hints you've used",
        "",
        "**During the Interview:**",
        "- Allow the candidate to think through the problem and ask clarifying questions",
        "- Encourage them to explain their thought process as they work",
        "- Be supportive but don't give away the solution",
        "- If they finish or get significantly stuck, move to the evaluation phase",
        "",
        "**Evaluation Criteria:**",
        "After the coding session, you will evaluate the candidate on three categories, each rated 1-5:",
        "",
        "1. **Code Cleanliness** - Consider readability, proper variable naming, code organization, and adherence to good coding practices",
        "2. **Communication** - Evaluate how well they explained their approach, asked clarifying questions, and walked through their solution",
        "3. **Efficiency** - Assess the time and space complexity of their solution and whether they considered optimization",
        "",
        "**Output Format:**",
        "When providing your evaluation, structure it as follows:",
        "",
        "For each category, first provide detailed feedback on what the candidate did well and areas for improvement, then give the numerical score. Use this format:",
        "",
        "<evaluation>",
        "**Code Cleanliness:**",
        "[Detailed feedback on code quality, naming conventions, structure, etc.]",
        "Score: [1-5]",
        "",
        "**Communication:**",
        "[Detailed feedback on how well they explained their thinking, asked questions, etc.]",
        "Score: [1-5]",
        "",
        "**Efficiency:**",
        "[Detailed feedback on algorithmic complexity, optimization considerations, etc.]",
        "Score: [1-5]",
        "",
        "**Overall Comments:**",
        "[Any additional feedback or suggestions for improvement]",
        "</evaluation>",
        "",
        "Remember to be constructive in your feedback and provide specific examples of what they could improve.",
        "",
        "BEGIN INTERVIEW",
    ]

    return "\n".join(part for part in parts if part is not None)

# ---------- Question loading (fallback by difficulty) ----------
def _find_questions_yaml() -> Path | None:
    base = Path(__file__).resolve().parents[1]  # mockly-backend
    for cand in [base / "app" / "questions.yaml", base / "questions.yaml"]:
        if cand.exists():
            return cand
    return None


def load_question_by_difficulty(difficulty: str) -> dict | None:
    if not difficulty:
        return None
    if _yaml is None:
        raise RuntimeError("PyYAML not installed; cannot load questions.yaml. Add PyYAML to requirements and install.")
    path = _find_questions_yaml()
    if not path:
        raise FileNotFoundError("questions.yaml not found under app/ or project root.")
    data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    diffs = data.get("difficulties") or []
    target = str(difficulty).strip().lower()
    for entry in diffs:
        if str(entry.get("difficulty", "")).strip().lower() == target:
            problems = entry.get("problems") or []
            if problems:
                q = dict(problems[0])
                q.setdefault("difficulty", difficulty)
                return q
            break
    return None

# ---------- Evaluation parsing helper ----------
import re as _re

def parse_evaluation_scores(text: str) -> dict:
    """
    Extract 1-5 numeric scores from an evaluation block. Returns keys:
    - code_cleanliness, communication, efficiency (ints if found)
    - raw (original text)
    """
    scores = {"code_cleanliness": None, "communication": None, "efficiency": None, "raw": text}
    if not text:
        return scores

    # Try to match 'Code Cleanliness' section
    cc = _re.search(r"Code\s*Cleanliness[\s\S]*?Score:\s*([1-5])", text, _re.IGNORECASE)
    com = _re.search(r"Communication[\s\S]*?Score:\s*([1-5])", text, _re.IGNORECASE)
    eff = _re.search(r"Efficiency[\s\S]*?Score:\s*([1-5])", text, _re.IGNORECASE)
    if cc:
        scores["code_cleanliness"] = int(cc.group(1))
    if com:
        scores["communication"] = int(com.group(1))
    if eff:
        scores["efficiency"] = int(eff.group(1))
    return scores

# ---------- Claude Streaming (SSE) ----------
def stream_claude_text(user_text: str, system_override: str | None = None) -> Iterable[str]:
    """
    Yields incremental text using Anthropic SDK's text_stream iterator.
    """
    with anthropic_client.messages.stream(
        model=ANTHROPIC_MODEL,
        system=(system_override or build_system_prompt_from_question({})),
        messages=[{"role": "user", "content": user_text}],
        max_tokens=1024
    ) as stream:
        for piece in getattr(stream, "text_stream", []) or []:
            if piece:
                yield piece

# ---------- Chunk streamed tokens into sentence-like pieces ----------
def sentence_chunks(token_iter: Iterable[str], min_chars: int = 24, first_flush_ms: int = 900) -> Iterable[str]:
    """
    Flush sooner by default: ~1s or ~24 chars if no punctuation seen yet.
    """
    buf, acc = [], 0
    first_started_at: float | None = None
    first_chunk_sent = False

    for tok in token_iter:
        if first_started_at is None:
            first_started_at = time.perf_counter()
        buf.append(tok)
        acc += len(tok)
        joined = "".join(buf)

        if re.search(r"[.!?]\s$", joined) or "\n" in joined or acc >= min_chars:
            out = joined.strip()
            if out:
                yield out
                first_chunk_sent = True
            buf, acc, first_started_at = [], 0, None
            continue

        if not first_chunk_sent and first_started_at is not None:
            elapsed_ms = (time.perf_counter() - first_started_at) * 1000.0
            if elapsed_ms >= first_flush_ms and joined.strip():
                yield joined.strip()
                buf, acc, first_started_at = [], 0, None
                first_chunk_sent = True

    if buf:
        out = "".join(buf).strip()
        if out:
            yield out

# ---------- TTS sanitization to avoid reading symbols aloud ----------
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

# ---------- Helper to  ----------
async def _send_chunks_via_ws(ws, sentences) -> None:
    """Send chunks using {'type':'Speak'} messages.
    Rate-limit Flush: only flush when enough text has accumulated
    or a minimum interval has elapsed; then Close at the end.
    """
    try:
        any_sent = False
        # Flush thresholds (tuneable)
        FLUSH_CHARS = 220
        FLUSH_MS = 650
        last_flush = time.perf_counter()
        pending_chars = 0

        # Async iterator path
        if hasattr(sentences, "__aiter__"):
            async for sentence in sentences:  # type: ignore[attr-defined]
                clean = sanitize_for_tts(str(sentence)).strip()
                if not clean:
                    continue
                payload = json.dumps({"type": "Speak", "text": clean})
                ws.send_text(payload)                       # <-- STRING JSON
                logging.info(f"[Deepgram WS] SENT Speak: {clean[:120]!r}")
                any_sent = True
                pending_chars += len(clean)
                now = time.perf_counter()
                if pending_chars >= FLUSH_CHARS or (now - last_flush) * 1000.0 >= FLUSH_MS:
                    ws.send_text(json.dumps({"type": "Flush"}))
                    logging.info("[Deepgram WS] SENT Flush")
                    pending_chars = 0
                    last_flush = now
                await asyncio.sleep(0)

        # Sync iterable path
        else:
            for sentence in sentences:  # type: ignore
                clean = sanitize_for_tts(str(sentence)).strip()
                if not clean:
                    continue
                payload = json.dumps({"type": "Speak", "text": clean})
                ws.send_text(payload)                       # <-- STRING JSON
                logging.info(f"[Deepgram WS] SENT Speak: {clean[:120]!r}")
                any_sent = True
                pending_chars += len(clean)
                now = time.perf_counter()
                if pending_chars >= FLUSH_CHARS or (now - last_flush) * 1000.0 >= FLUSH_MS:
                    ws.send_text(json.dumps({"type": "Flush"}))
                    logging.info("[Deepgram WS] SENT Flush")
                    pending_chars = 0
                    last_flush = now
                await asyncio.sleep(0)
    finally:
        # Final Flush if there is pending content
        with contextlib.suppress(Exception):
            ws.send_text(json.dumps({"type": "Flush"}))
            logging.info("[Deepgram WS] SENT Flush (final)")
        # Close after sending chunks
        ws.send_text(json.dumps({"type": "Close"}))         # <-- STRING JSON
        logging.info("[Deepgram WS] SENT Close")

# ---------- Deepgram TTS — WebSocket streaming (robust & SDK-agnostic) ----------
async def stream_deepgram_tts(sentences) -> AsyncIterator[bytes]:
    q: asyncio.Queue[bytes] = asyncio.Queue()
    closed = {"flag": False}
    saw_audio = {"flag": False}

    def on_message(msg):
        if isinstance(msg, (bytes, bytearray)):
            saw_audio["flag"] = True
            q.put_nowait(bytes(msg)); return
        mtype = getattr(msg, "type", None) or getattr(msg, "_type", None)
        data  = getattr(msg, "data", None)
        if str(mtype).lower() == "audio" and isinstance(data, (bytes, bytearray)):
            saw_audio["flag"] = True
            q.put_nowait(bytes(data)); return
        logging.info(f"[Deepgram WS] non-audio: {msg!r}")

    with dg.speak.v1.connect(
        model=DEEPGRAM_TTS_VOICE,
        encoding=DEEPGRAM_STREAM_ENCODING,
        sample_rate=DEEPGRAM_SAMPLE_RATE,
    ) as ws:
        ws.on(EventType.OPEN,   lambda _: logging.info("[Deepgram WS] OPEN"))
        ws.on(EventType.MESSAGE, on_message)
        ws.on(EventType.CLOSE,  lambda _: (closed.update({"flag": True}), logging.info("[Deepgram WS] CLOSE")))
        ws.on(EventType.ERROR,  lambda e: logging.error(f"[Deepgram WS] ERROR: {e}"))
        ws.start_listening()

        send_task = asyncio.create_task(_send_chunks_via_ws(ws, sentences))

        last = time.perf_counter(); total = 0
        while True:
            try:
                frame = await asyncio.wait_for(q.get(), timeout=0.8)
                total += len(frame)
                if total // 32768 != (total - len(frame)) // 32768:
                    logging.info(f"[Deepgram WS] audio {total/1024:.1f} KiB")
                yield frame
                last = time.perf_counter()
            except asyncio.TimeoutError:
                if closed["flag"] and (time.perf_counter() - last) > 0.8:
                    break

        if not send_task.done():
            send_task.cancel()
            with contextlib.suppress(Exception):
                await send_task

    if not saw_audio["flag"]:
        logging.warning("[Deepgram WS] no audio frames were received")

# ---------- Deepgram TTS – Raw WebSocket pipeline (no SDK) ----------
async def stream_deepgram_tts_raw(sentences: Iterable[str]) -> AsyncIterator[bytes]:
    try:
        import websockets  # type: ignore
    except Exception:
        raise HTTPException(500, "Missing dependency 'websockets'. Install with: pip install websockets")

    from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError  # type: ignore

    url = (
        f"wss://api.beta.deepgram.com/v1/speak?"
        f"model={DEEPGRAM_TTS_VOICE}&encoding={DEEPGRAM_STREAM_ENCODING}&sample_rate={DEEPGRAM_SAMPLE_RATE}"
    )
    headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]

    # Older websockets versions may not accept extra_headers and raise TypeError
    try:
        connect_ctx = websockets.connect(url, extra_headers=headers, max_size=None)  # type: ignore
    except TypeError as e:
        # Provide a clear remediation path
        raise HTTPException(
            500,
            "Incompatible 'websockets' package: missing support for extra_headers. "
            "Upgrade with: pip install -U websockets (>=12)."
        ) from e

    async with connect_ctx as ws:  # type: ignore
        async def sender() -> None:
            any_sent = False
            FLUSH_CHARS = 220
            FLUSH_MS = 650
            last_flush = time.perf_counter()
            pending_chars = 0
            try:
                if hasattr(sentences, "__aiter__"):
                    async for sentence in sentences:  # type: ignore[attr-defined]
                        clean = sanitize_for_tts(str(sentence)).strip()
                        if not clean:
                            continue
                        await ws.send(json.dumps({"type": "Speak", "text": clean}))
                        logging.info(f"[Deepgram WS raw] SENT Speak: {clean[:120]!r}")
                        any_sent = True
                        pending_chars += len(clean)
                        now = time.perf_counter()
                        if pending_chars >= FLUSH_CHARS or (now - last_flush) * 1000.0 >= FLUSH_MS:
                            await ws.send(json.dumps({"type": "Flush"}))
                            logging.info("[Deepgram WS raw] SENT Flush")
                            pending_chars = 0
                            last_flush = now
                        await asyncio.sleep(0)
                else:
                    for sentence in sentences:  # type: ignore[assignment]
                        clean = sanitize_for_tts(str(sentence)).strip()
                        if not clean:
                            continue
                        await ws.send(json.dumps({"type": "Speak", "text": clean}))
                        logging.info(f"[Deepgram WS raw] SENT Speak: {clean[:120]!r}")
                        any_sent = True
                        pending_chars += len(clean)
                        now = time.perf_counter()
                        if pending_chars >= FLUSH_CHARS or (now - last_flush) * 1000.0 >= FLUSH_MS:
                            await ws.send(json.dumps({"type": "Flush"}))
                            logging.info("[Deepgram WS raw] SENT Flush")
                            pending_chars = 0
                            last_flush = now
                        await asyncio.sleep(0)
                # No final Flush necessary since we flush per chunk
            except Exception:
                pass
        
        send_task = asyncio.create_task(sender())

        # Idle-cutoff: after sender finishes and no audio for ~1s, end
        last_audio = time.perf_counter()
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.2)
                except asyncio.TimeoutError:
                    if send_task.done() and (time.perf_counter() - last_audio) > 1.0:
                        break
                    continue
                except ConnectionClosedOK:
                    break
                except ConnectionClosedError:
                    break

                if isinstance(msg, (bytes, bytearray)):
                    last_audio = time.perf_counter()
                    yield bytes(msg)
                else:
                    try:
                        logging.info(f"[Deepgram WS raw] text: {msg}")
                    except Exception:
                        pass
        finally:
            # Final flush after last chunk if any pending
            with contextlib.suppress(Exception):
                await ws.send(json.dumps({"type": "Flush"}))
                logging.info("[Deepgram WS raw] SENT Flush (final)")
            # Ask the server to close the stream
            with contextlib.suppress(Exception):
                await ws.send(json.dumps({"type": "Close"}))
                logging.info("[Deepgram WS raw] SENT Close")
            # Also close client side so recv() unblocks on some servers
            with contextlib.suppress(Exception):
                await ws.close()
            if not send_task.done():
                send_task.cancel()
                with contextlib.suppress(Exception):
                    await send_task

# ---------- Streaming endpoint: Text -> Claude(SSE) -> Deepgram TTS(WS) ----------
@app.post("/type/stream")
def type_streaming(data: dict):
    user_text = (data.get("text") or "").strip()
    question = data.get("question")  # optional: dict with question context from questions.yaml
    if not question and data.get("difficulty"):
        question = load_question_by_difficulty(str(data.get("difficulty")))
    system = build_system_prompt_from_question(question)
    # Allow starting by difficulty only; default the first user turn
    if not user_text:
        if data.get("difficulty") or question:
            user_text = "BEGIN INTERVIEW"
        else:
            raise HTTPException(400, "Field 'text' is required.")

    async def audio_iter():
        # 1) stream Claude tokens
        tokens = stream_claude_text(user_text, system_override=system)
        # 2) group into sentence-like chunks
        chunks = sentence_chunks(tokens)
        # 3) stream TTS audio frames as they arrive (raw WS pipeline)
        async for audio in stream_deepgram_tts_raw(chunks):
            yield audio

    # For WS TTS with linear16, we stream raw PCM frames.
    # Your frontend/talking head should consume this stream as raw PCM.
    # (If your FE needs a container like MP3/WAV, use a WS on the FE or a media muxer.)
    media_type = "application/octet-stream"
    return StreamingResponse(audio_iter(), media_type=f"audio/L16; rate={DEEPGRAM_SAMPLE_RATE}; channels=1",)

# ---------- Debug: TTS only (send fixed text) ----------
@app.get("/debug/tts")
async def debug_tts():
    async def audio_iter():
        test_sentences = [
            "Testing the voice connection. You should hear this shortly.",
            "If you can hear this, Deepgram streaming is working.",
        ]
        async for audio in stream_deepgram_tts(test_sentences):
            yield audio
    return StreamingResponse(audio_iter(), media_type="application/octet-stream")

@app.get("/debug/tts-min")
async def debug_tts_min():
    async def audio_iter():
        from deepgram.extensions.types.sockets import (
            SpeakV1SocketClientResponse,
            SpeakV1TextMessage,
            SpeakV1ControlMessage,
        )
        import asyncio, time, logging
        q: asyncio.Queue[bytes] = asyncio.Queue()
        closed = {"flag": False}

        def on_message(msg: SpeakV1SocketClientResponse):
            # audio as raw bytes
            if isinstance(msg, bytes):
                q.put_nowait(msg)
                return
            # audio as typed "Audio" message (some SDK builds)
            mtype = getattr(msg, "type", None) or getattr(msg, "_type", None)
            data  = getattr(msg, "data", None)
            if str(mtype).lower() == "audio" and isinstance(data, (bytes, bytearray)):
                q.put_nowait(bytes(data))
                return
            logging.info(f"[Deepgram WS] non-audio: {msg!r}")

        with dg.speak.v1.connect(
            model=DEEPGRAM_TTS_VOICE,
            encoding=DEEPGRAM_STREAM_ENCODING,
            sample_rate=DEEPGRAM_SAMPLE_RATE,
        ) as ws:
            ws.on(EventType.OPEN,  lambda _: logging.info("[Deepgram WS] OPEN"))
            ws.on(EventType.MESSAGE, on_message)
            ws.on(EventType.CLOSE, lambda _: (closed.update({"flag": True}), logging.info("[Deepgram WS] CLOSE")))
            ws.on(EventType.ERROR, lambda e: logging.error(f"[Deepgram WS] ERROR: {e}"))
            ws.start_listening()

            text = "This is a streaming test from Deepgram continuous text."
            ws.send_text(SpeakV1TextMessage(text=text))
            logging.info(f"[Deepgram WS] SENT Text: {text!r}")
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

    return StreamingResponse(
        audio_iter(),
        media_type=f"audio/L16; rate={DEEPGRAM_SAMPLE_RATE}; channels=1",
    )   

# ---------- Debug: stream only Claude text (no TTS) ----------
@app.post("/debug/claude/stream")
def debug_claude_stream(data: dict):
    user_text = (data.get("text") or "").strip()
    question = data.get("question")
    if not question and data.get("difficulty"):
        question = load_question_by_difficulty(str(data.get("difficulty")))
    system = build_system_prompt_from_question(question)
    # Allow starting by difficulty only; default the first user turn
    if not user_text:
        if data.get("difficulty") or question:
            user_text = "BEGIN INTERVIEW"
        else:
            raise HTTPException(400, "Field 'text' is required.")

    def iter_text():
        for piece in stream_claude_text(user_text, system_override=system):
            # yield as plain text stream
            yield piece

    return StreamingResponse(iter_text(), media_type="text/plain; charset=utf-8")

@app.get("/debug/tts-direct")
async def debug_tts_direct():
    async def audio_iter():
        async def one():
            yield "This is a direct Speak test."
        async for b in stream_deepgram_tts(one()):
            yield b
    return StreamingResponse(
        audio_iter(),
        media_type=f"audio/L16; rate={DEEPGRAM_SAMPLE_RATE}; channels=1",
    )

@app.get("/debug/tts-raw")
async def debug_tts_raw():
    """
    Deepgram WS minimal test (no Claude, no helpers).
    Sends one Speak -> Flush -> Close and streams raw PCM bytes back.
    """
    import json, asyncio, time, logging
    from fastapi.responses import StreamingResponse
    from deepgram.core.events import EventType

    q: asyncio.Queue[bytes] = asyncio.Queue()
    closed = {"flag": False}

    def on_message(msg):
        # Raw audio bytes
        if isinstance(msg, (bytes, bytearray)):
            q.put_nowait(bytes(msg)); return

        # Some SDKs wrap frames as typed "Audio" events
        mtype = getattr(msg, "type", None) or getattr(msg, "_type", None)
        data  = getattr(msg, "data", None)
        if str(mtype).lower() == "audio" and isinstance(data, (bytes, bytearray)):
            q.put_nowait(bytes(data)); return

        # Log any JSON/control events (Metadata/Warning/Error/Flushed/etc.)
        logging.info(f"[Deepgram WS] non-audio: {msg!r}")

    def open_ws():
        return dg.speak.v1.connect(
            model=DEEPGRAM_TTS_VOICE,
            encoding=DEEPGRAM_STREAM_ENCODING,
            sample_rate=DEEPGRAM_SAMPLE_RATE,
        )

    async def audio_iter():
        nonlocal q, closed
        with open_ws() as ws:
            ws.on(EventType.OPEN,   lambda _: logging.info("[Deepgram WS] OPEN"))
            ws.on(EventType.MESSAGE, on_message)
            ws.on(EventType.CLOSE,  lambda _: (closed.update({"flag": True}), logging.info("[Deepgram WS] CLOSE")))
            ws.on(EventType.ERROR,  lambda e: logging.error(f"[Deepgram WS] ERROR: {e}"))
            ws.start_listening()

            # === Send exactly what the Deepgram sample uses ===
            speak_payload = json.dumps({"type": "Speak", "text": "This is a direct Speak test."})
            ws.send_text(speak_payload)
            logging.info(f"[Deepgram WS] SENT Speak: {speak_payload}")

            ws.send_text(json.dumps({"type": "Flush"}))
            logging.info("[Deepgram WS] SENT Flush")

            # tiny pause is fine; socket stays open while we drain frames
            await asyncio.sleep(0.05)

            ws.send_text(json.dumps({"type": "Close"}))
            logging.info("[Deepgram WS] SENT Close")

            # Drain frames until CLOSE + short idle
            last = time.perf_counter()
            while True:
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=0.8)
                    yield frame
                    last = time.perf_counter()
                except asyncio.TimeoutError:
                    if closed["flag"] and (time.perf_counter() - last) > 0.8:
                        break

    return StreamingResponse(
        audio_iter(),
        media_type=f"audio/L16; rate={DEEPGRAM_SAMPLE_RATE}; channels=1",
    )

# ---------- Non-streaming endpoint for comparison ----------
@app.post("/type")
async def type_to_voice(request: Request):
    """
    Simpler path: full Claude reply first, then TTS (blocking).
    Useful as a baseline for latency comparisons.
    """
    data = await request.json()
    user_text = (data.get("text") or "").strip()
    question = data.get("question")  # optional dict
    if not question and data.get("difficulty"):
        question = load_question_by_difficulty(str(data.get("difficulty")))
    system = build_system_prompt_from_question(question)
    if not user_text:
        if data.get("difficulty") or question:
            user_text = "BEGIN INTERVIEW"
        else:
            raise HTTPException(400, "Field 'text' is required.")

    # Get complete text (non-streaming)
    msg = anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        system=system,
        messages=[{"role": "user", "content": user_text}],
        max_tokens=800,
        # no `thinking` => extended reasoning OFF
    )
    full_text = "".join([b.text for b in msg.content if getattr(b, "type", "") == "text"])
    full_text = sanitize_for_tts(full_text)

    # Use Deepgram SDK for a single-shot audio file (mp3) - handle multiple return shapes
    try:
        gen_or_resp = dg.speak.v1.audio.generate(
            text=full_text,
            model=DEEPGRAM_TTS_VOICE,
            encoding="mp3",
        )
        audio: bytes | None = None
        stream_attr = getattr(gen_or_resp, "stream", None)
        if stream_attr is not None and hasattr(stream_attr, "getvalue"):
            audio = stream_attr.getvalue()
        elif isinstance(gen_or_resp, (bytes, bytearray)):
            audio = bytes(gen_or_resp)
        else:
            # iterable/generator of bytes
            try:
                chunks = []
                for part in gen_or_resp:  # type: ignore
                    if isinstance(part, (bytes, bytearray)):
                        chunks.append(bytes(part))
                audio = b"".join(chunks) if chunks else None
            except TypeError:
                audio = None
        if not audio:
            raise RuntimeError("Deepgram TTS returned no audio bytes")
    except Exception as e:
        logging.exception(f"Deepgram TTS generation failed: {e}")
        raise HTTPException(500, "TTS generation failed")

    return Response(content=audio, media_type="audio/mpeg")

@app.get("/health")
def health():
    return {"ok": True}

# ---------- FE helper: audio config ----------
@app.get("/audio/config")
def audio_config():
    return {
        "encoding": DEEPGRAM_STREAM_ENCODING,
        "sample_rate": DEEPGRAM_SAMPLE_RATE,
        "channels": 1,
        "content_type": f"audio/L16; rate={DEEPGRAM_SAMPLE_RATE}; channels=1",
    }

# ---------- Route aliases under /api prefix (to match FE proxy) ----------
# These mirror existing endpoints so the frontend can call /api/*
app.add_api_route("/api/health", health, methods=["GET"])
app.add_api_route("/api/audio/config", audio_config, methods=["GET"])

# Core streaming endpoints
app.add_api_route("/api/input/stream", input_stream, methods=["POST"])
app.add_api_route("/api/type/stream", type_streaming, methods=["POST"])
app.add_api_route("/api/type", type_to_voice, methods=["POST"])

# Debug helpers
app.add_api_route("/api/debug/claude/stream", debug_claude_stream, methods=["POST"])
app.add_api_route("/api/debug/tts", debug_tts, methods=["GET"])
app.add_api_route("/api/debug/tts-min", debug_tts_min, methods=["GET"])
app.add_api_route("/api/eval/parse", eval_parse, methods=["POST"])

# ---------- Utility endpoint: parse evaluation scores ----------
@app.post("/eval/parse")
async def eval_parse(request: Request):
    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "Field 'text' is required.")
    return {"scores": parse_evaluation_scores(text)}

# ---------- Deepgram STT (prerecorded) minimal helper ----------
async def transcribe_prerecorded_deepgram(audio_bytes: bytes, content_type: str = "audio/wav") -> str:
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": content_type,
    }
    params = {"model": (os.getenv("DEEPGRAM_STT_MODEL") or "nova-3")}
    url = "https://api.deepgram.com/v1/listen"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, params=params, headers=headers, content=audio_bytes)
        r.raise_for_status()
        data = r.json()
    try:
        return data["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception:
        logging.error(f"Unexpected Deepgram STT response: {data}")
        raise HTTPException(500, "STT failed to return transcript")

# ---------- Unified input: text or voice -> Claude -> Deepgram TTS ----------
@app.post("/input/stream")
def input_stream(payload: dict = Body(...)):
    """
    Unified entry. Body supports either:
      - {"mode":"text", "text":"...", "difficulty":"easy"}
      - {"mode":"voice", "audio_b64":"...", "mime":"audio/wav", "difficulty":"easy"}
    Optional: "question" object instead of difficulty.
    Streams audio PCM from Deepgram TTS.
    """
    mode = (payload.get("mode") or "text").strip().lower()
    question = payload.get("question")
    if not question and payload.get("difficulty"):
        question = load_question_by_difficulty(str(payload.get("difficulty")))
    system = build_system_prompt_from_question(question)

    async def audio_iter():
        # Resolve the initial user_text based on mode
        user_text: str
        if mode == "voice":
            b64 = payload.get("audio_b64")
            if not b64:
                raise HTTPException(400, "audio_b64 required for voice mode")
            try:
                audio_bytes = base64.b64decode(b64)
            except Exception:
                raise HTTPException(400, "audio_b64 is invalid base64")
            mime = (payload.get("mime") or "audio/wav").strip() or "audio/wav"
            # Transcribe via Deepgram prerecorded API
            user_text = await transcribe_prerecorded_deepgram(audio_bytes, content_type=mime)
            if not user_text:
                raise HTTPException(400, "Transcription returned empty text")
        else:
            user_text = (payload.get("text") or "").strip()
            if not user_text:
                # default starter when only difficulty/question supplied
                user_text = "BEGIN INTERVIEW"

        # Claude tokens
        tokens = stream_claude_text(user_text, system_override=system)
        chunks = sentence_chunks(tokens)
        async for audio in stream_deepgram_tts_raw(chunks):
            yield audio

    return StreamingResponse(
        audio_iter(),
        media_type=f"audio/L16; rate={DEEPGRAM_SAMPLE_RATE}; channels=1",
    )


