from fastapi import APIRouter, HTTPException
from .models import WebRtcOfferPayload, WebRtcSessionResponse, WebRtcCandidatePayload
import uuid


router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])


# Minimal in-memory session store for demo purposes only
_SESSIONS: dict[str, dict] = {}


@router.post("/offer", response_model=WebRtcSessionResponse)
async def create_webrtc_session(payload: WebRtcOfferPayload) -> WebRtcSessionResponse:
    """
    This is a *signaling* endpoint. For a real implementation, you would parse the
    incoming SDP offer, create an RTCPeerConnection server-side (e.g., with aiortc),
    and generate a *real* SDP answer. For now, we echo back the SDP as the answer so
    the front-end can proceed in mock mode.
    """
    session_id = uuid.uuid4().hex
    _SESSIONS[session_id] = {"offer": payload.sdp, "candidates": []}
    # Placeholder answer: echo the offer; replace with aiortc to negotiate.
    return WebRtcSessionResponse(answer=payload.sdp, sessionId=session_id, iceServers=[])




@router.post("/candidate")
async def send_candidate(payload: WebRtcCandidatePayload) -> dict:
    sess = _SESSIONS.get(payload.sessionId)
    if not sess:
        raise HTTPException(status_code=404, detail="Unknown sessionId")
    sess["candidates"].append(payload.candidate)
    return {"ok": True}




@router.delete("/session/{session_id}")
async def close_session(session_id: str) -> dict:
    _SESSIONS.pop(session_id, None)
    return {"ok": True} 