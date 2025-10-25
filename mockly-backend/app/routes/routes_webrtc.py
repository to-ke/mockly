from fastapi import APIRouter, HTTPException

from ..models import WebRtcCandidatePayload, WebRtcOfferPayload, WebRtcSessionResponse
from ..services.webrtc_manager import manager


router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])


@router.post("/offer", response_model=WebRtcSessionResponse)
async def create_webrtc_session(payload: WebRtcOfferPayload) -> WebRtcSessionResponse:
    session_id, pc = await manager.create_session(payload.sdp, payload.type)
    answer = pc.localDescription
    return WebRtcSessionResponse(answer=answer.sdp, sessionId=session_id, iceServers=[])


@router.post("/candidate")
async def send_candidate(payload: WebRtcCandidatePayload) -> dict:
    try:
        await manager.add_candidate(payload.sessionId, payload.candidate)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown sessionId") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/session/{session_id}")
async def get_session_stats(session_id: str) -> dict:
    stats = manager.get_stats(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Unknown sessionId")
    return stats


@router.delete("/session/{session_id}")
async def close_session(session_id: str) -> dict:
    await manager.close_session(session_id)
    return {"ok": True}
