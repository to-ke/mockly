import { Api } from '@/services/api'


const useMock = import.meta.env.VITE_USE_MOCK === 'true'


export class AudioStreamer {
    private peerConnection: RTCPeerConnection | null = null
    private localStream: MediaStream | null = null
    private sessionId: string | null = null
    private connectionPromise: Promise<void> | null = null
    private muted = true


    get isActive() {
        return Boolean(this.peerConnection && this.localStream)
    }


    async setMuted(muted: boolean) {
        this.muted = muted
        if (!muted) {
            await this.ensureConnection()
        }
        this.applyMuteState()
    }


    async warmup(options?: { muted?: boolean }) {
        if (typeof options?.muted === 'boolean') {
            this.muted = options.muted
        }
        await this.ensureConnection()
        this.applyMuteState()
    }


    async stop() {
        this.connectionPromise = null
        this.muted = true

        if (this.localStream) {
            this.localStream.getTracks().forEach((track) => track.stop())
        }
        this.localStream = null

        if (this.peerConnection) {
            this.peerConnection.getSenders().forEach((sender) => sender.track?.stop())
            this.peerConnection.close()
        }
        this.peerConnection = null

        if (!useMock && this.sessionId) {
            try {
                await Api.closeWebRtcSession(this.sessionId)
            } catch (error) {
                console.warn('Failed to notify backend about closing session', error)
            }
        }

        this.sessionId = null
    }


    private async ensureConnection() {
        if (this.peerConnection) return
        if (this.connectionPromise) {
            await this.connectionPromise
            return
        }
        this.connectionPromise = this.bootstrapConnection()
        try {
            await this.connectionPromise
        } finally {
            this.connectionPromise = null
        }
    }


    private async bootstrapConnection() {
        if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error('Audio capture is not supported in this browser.')
        }

        this.localStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                noiseSuppression: true,
                echoCancellation: true,
            },
            video: false,
        })

        this.peerConnection = new RTCPeerConnection()
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendIceCandidate(event.candidate).catch((err) => {
                    console.error('Failed to send ICE candidate', err)
                })
            }
        }

        this.localStream.getTracks().forEach((track) => {
            if (this.peerConnection) {
                this.peerConnection.addTrack(track, this.localStream as MediaStream)
            }
        })
        this.applyMuteState()

        const offer = await this.peerConnection.createOffer()
        await this.peerConnection.setLocalDescription(offer)

        if (useMock) {
            console.info('[Mockly] Audio streaming mocked; no backend call made.')
            return
        }

        const localDescription = this.peerConnection.localDescription ?? offer
        if (!localDescription?.sdp) {
            throw new Error('Unable to create WebRTC offer SDP.')
        }

        const result = await Api.createWebRtcSession({
            sdp: localDescription.sdp,
            type: localDescription.type,
        })
        this.sessionId = result.sessionId

        if (!result.answer) {
            throw new Error('Missing SDP answer from signaling server.')
        }

        if (result.iceServers && this.peerConnection) {
            const configuration: RTCConfiguration = { iceServers: result.iceServers }
            this.peerConnection.setConfiguration(configuration)
        }

        await this.peerConnection.setRemoteDescription(
            new RTCSessionDescription({ type: 'answer', sdp: result.answer })
        )
    }


    private applyMuteState() {
        if (!this.localStream) return
        const enabled = !this.muted
        this.localStream.getAudioTracks().forEach((track) => {
            track.enabled = enabled
        })
    }


    private async sendIceCandidate(candidate: RTCIceCandidate) {
        if (useMock || !this.sessionId) return
        await Api.sendWebRtcCandidate({
            sessionId: this.sessionId,
            candidate: candidate.toJSON(),
        })
    }
}
