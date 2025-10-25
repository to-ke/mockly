from __future__ import annotations
from typing import Literal, Optional, List, Dict
from pydantic import BaseModel


# --- Questions ---
class QuestionRequest(BaseModel):
    difficulty: Literal["easy", "medium", "hard"]


class QuestionPayload(BaseModel):
    id: str
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str
    starter_code: Optional[str] = None
    language: Optional[str] = None
    answers: Optional[List[str]] = None


# --- Code execution ---
class ExecuteRequest(BaseModel):
    language: Literal["python", "javascript", "typescript", "cpp", "java"]
    source: str
    stdin: Optional[str] = None
    timeoutMs: Optional[int] = None


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    exitCode: int
    timeMs: Optional[int] = None


# --- Feedback ---
class FeedbackReport(BaseModel):
    communication: int
    codeCleanliness: int
    codeEfficiency: int
    comments: str


# --- WebRTC signaling ---
class WebRtcOfferPayload(BaseModel):
    sdp: str
    type: Literal["offer", "answer", "pranswer", "rollback"] = "offer"


class WebRtcSessionResponse(BaseModel):
    answer: str
    sessionId: str
    iceServers: Optional[List[Dict]] = None


class WebRtcCandidatePayload(BaseModel):
    sessionId: str
    candidate: Dict
