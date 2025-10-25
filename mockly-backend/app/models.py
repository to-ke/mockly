from __future__ import annotations
from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, Field


# --- Execute ---
class ExecuteRequest(BaseModel):
    language: Literal["python", "javascript", "typescript", "java", "cpp"]
    source: str
    stdin: Optional[str] = ""
    filename: Optional[str] = None  # optional hint for file naming
    timeout_ms: int = Field(default=4000, alias="timeoutMs")
    memory_limit_mb: int = Field(default=256, alias="memoryLimitMb")

    class Config:
        allow_population_by_field_name = True


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    exitCode: int
    timeMs: Optional[int] = None


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
