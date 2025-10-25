import asyncio
import contextlib
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional

from aiortc.sdp import candidate_from_sdp
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

logger = logging.getLogger(__name__)


@dataclass
class WebRtcSessionState:
    pc: RTCPeerConnection
    tasks: List[asyncio.Task] = field(default_factory=list)
    last_audio_timestamp: Optional[float] = None
    frames_received: int = 0
    audio_events: Deque[float] = field(default_factory=lambda: deque(maxlen=50))


class WebRtcManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, WebRtcSessionState] = {}

    async def create_session(self, sdp: str, sdp_type: str) -> tuple[str, RTCPeerConnection]:
        session_id = uuid.uuid4().hex
        pc = RTCPeerConnection()
        state = WebRtcSessionState(pc=pc)
        self._sessions[session_id] = state

        @pc.on("track")
        def on_track(track) -> None:
            if track.kind != "audio":
                logger.info("Session %s: received non-audio track (%s), ignoring", session_id, track.kind)
                return
            logger.info("Session %s: audio track connected", session_id)
            task = asyncio.create_task(self._consume_audio(session_id, track))
            state.tasks.append(task)

        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=sdp_type))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        return session_id, pc

    async def add_candidate(self, session_id: str, candidate_payload: Optional[dict]) -> None:
        state = self._sessions.get(session_id)
        if not state:
            raise KeyError(session_id)

        if not candidate_payload:
            await state.pc.addIceCandidate(None)
            return

        candidate = self._parse_ice_candidate(candidate_payload)
        await state.pc.addIceCandidate(candidate)

    async def close_session(self, session_id: str) -> None:
        state = self._sessions.pop(session_id, None)
        if not state:
            return

        for task in state.tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        await state.pc.close()

    def get_stats(self, session_id: str) -> Optional[dict]:
        state = self._sessions.get(session_id)
        if not state:
            return None

        return {
            "sessionId": session_id,
            "connectionState": state.pc.connectionState,
            "signalingState": state.pc.signalingState,
            "framesReceived": state.frames_received,
            "lastAudioTimestamp": state.last_audio_timestamp,
            "recentAudioTimestamps": list(state.audio_events),
        }

    async def _consume_audio(self, session_id: str, track) -> None:
        state = self._sessions.get(session_id)
        if not state:
            return

        try:
            while True:
                _ = await track.recv()
                state.frames_received += 1
                state.last_audio_timestamp = time.time()
                state.audio_events.append(state.last_audio_timestamp)
                if state.frames_received % 60 == 0:
                    logger.info(
                        "Session %s: received %s audio frames (latest at %s)",
                        session_id,
                        state.frames_received,
                        state.last_audio_timestamp,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.info("Session %s: audio track ended (%s)", session_id, exc)

    @staticmethod
    def _parse_ice_candidate(payload: dict) -> RTCIceCandidate:
        """
        Convert a browser-style ICE payload into an aiortc RTCIceCandidate.
        Accepts payloads like:
        { candidate: "candidate:...", sdpMid: "audio", sdpMLineIndex: 0 }
        or legacy variants with keys 'id'/'label'.
        """
        cand = payload.get("candidate")
        if cand is None:
            raise ValueError("ICE candidate payload missing 'candidate' field")

        # Some clients send "candidate:" prefix; strip it if present
        if cand.startswith("candidate:"):
            cand = cand.split(":", 1)[1]

        # Build aiortc RTCIceCandidate from the SDP fragment
        rtc_cand = candidate_from_sdp(cand)

        # Populate mid / mline index (aiortc requires one of these)
        rtc_cand.sdpMid = payload.get("sdpMid") or payload.get("id")
        rtc_cand.sdpMLineIndex = payload.get("sdpMLineIndex") or payload.get("label")

        if rtc_cand.sdpMid is None and rtc_cand.sdpMLineIndex is None:
            raise ValueError("ICE candidate missing sdpMid/sdpMLineIndex")

        return rtc_cand


# Singleton manager for router modules to import.
manager = WebRtcManager()
