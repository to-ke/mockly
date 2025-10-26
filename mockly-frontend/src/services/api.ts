import type { ExecuteRequest, ExecuteResponse, QuestionResponse } from '@/types/api'
import type { Difficulty, FeedbackReport } from '@/stores/app'

// Prefer talking directly to the backend in the browser to avoid
// proxy flakiness when the Vite dev server restarts. Fall back to the
// Vite proxy path ("/api") if we cannot infer a backend origin.
function resolveApiBase(): string {
    // Explicit override first
    const explicit = (import.meta as any).env?.VITE_BACKEND_ORIGIN as string | undefined
    if (explicit && /^https?:\/\//i.test(explicit)) {
        return explicit.replace(/\/$/, '') + '/api'
    }

    // Common dev setup: app runs on :5173, backend on :8000
    try {
        const loc = window.location
        if (loc.port === '5173') {
            const host = loc.hostname || 'localhost'
            return `http://${host}:8000/api`
        }
    } catch (_) {
        // window not available (SSR) — just fall back
    }

    // Fallback to proxy path; Vite will forward to backend if configured
    return '/api'
}

const API_BASE = resolveApiBase()

interface WebRtcOfferPayload {
    sdp: string
    type: RTCSdpType
}

interface WebRtcCandidatePayload {
    sessionId: string
    candidate: RTCIceCandidateInit
}

interface WebRtcSessionResponse {
    answer: string
    sessionId: string
    iceServers?: RTCIceServer[]
}


const useMock = import.meta.env.VITE_USE_MOCK === 'true'


async function mockExecute(payload: ExecuteRequest): Promise<ExecuteResponse> {
    // Simulate compile/run latency
    await new Promise(r => setTimeout(r, 500))


    if (!payload.source.trim()) {
        return { stdout: '', stderr: 'No source provided', exitCode: 1 }
    }


    // Tiny pretend runner
    const banner = `Running ${payload.language}...\n`;
    const echo = payload.source.split('\n').slice(0, 5).join('\n')
    return {
        stdout: banner + echo + (payload.stdin ? `\n\n<stdin>\n${payload.stdin}` : ''),
        stderr: '',
        exitCode: 0,
        timeMs: 42,
    }
}


export const Api = {
    async execute(payload: ExecuteRequest): Promise<ExecuteResponse> {
        if (useMock) return mockExecute(payload)


        const res = await fetch(`${API_BASE}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
        if (!res.ok) {
            const text = await res.text()
            throw new Error(text || res.statusText)
        }
        return res.json() as Promise<ExecuteResponse>
    },
    async fetchQuestion(payload: { difficulty: Difficulty; language?: string }): Promise<QuestionResponse> {
        if (useMock) {
            await new Promise((resolve) => setTimeout(resolve, 400))
            return {
                id: `mock-${payload.difficulty}`,
                difficulty: payload.difficulty,
                prompt: `Mock ${payload.difficulty} question will appear here.`,
                starter_code: 'def solution():\n    # Your code here\n    pass',
                language: payload.language || 'python',
            }
        }

        const res = await fetch(`${API_BASE}/questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
        if (!res.ok) {
            const text = await res.text()
            throw new Error(text || res.statusText)
        }
        return res.json() as Promise<QuestionResponse>
    },
    async fetchFeedback(): Promise<FeedbackReport> {
        if (useMock) {
            await new Promise((resolve) => setTimeout(resolve, 600))
            return {
                communication: 4,
                codeCleanliness: 5,
                codeEfficiency: 4,
                comments:
                    'Strong communication throughout the session with clear explanations. Code was well structured and easy to follow. Consider optimising your solution to reduce time complexity in future iterations.',
            }
        }

        const res = await fetch(`${API_BASE}/feedback`, { method: 'GET' })
        if (!res.ok) {
            const text = await res.text()
            throw new Error(text || res.statusText)
        }
        return res.json() as Promise<FeedbackReport>
    },
    async createWebRtcSession(payload: WebRtcOfferPayload): Promise<WebRtcSessionResponse> {
        if (useMock) {
            await new Promise((resolve) => setTimeout(resolve, 150))
            return {
                answer: payload.sdp,
                sessionId: 'mock-session',
                iceServers: [],
            }
        }

        const res = await fetch(`${API_BASE}/webrtc/offer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
        if (!res.ok) {
            const text = await res.text()
            throw new Error(text || res.statusText)
        }
        return res.json() as Promise<WebRtcSessionResponse>
    },
    async sendWebRtcCandidate(payload: WebRtcCandidatePayload): Promise<void> {
        if (useMock) return
        const res = await fetch(`${API_BASE}/webrtc/candidate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
        if (!res.ok) {
            const text = await res.text()
            throw new Error(text || res.statusText)
        }
    },
    async closeWebRtcSession(sessionId: string): Promise<void> {
        if (useMock) return
        const res = await fetch(`${API_BASE}/webrtc/session/${sessionId}`, { method: 'DELETE' })
        if (!res.ok) {
            const text = await res.text()
            throw new Error(text || res.statusText)
        }
    },
}
