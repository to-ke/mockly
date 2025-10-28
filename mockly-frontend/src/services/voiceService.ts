import type { Difficulty } from '@/stores/app'

interface VoiceServiceConfig {
    apiBase: string
    sampleRate?: number
    mimeType?: string
}

/**
 * VoiceService handles push-to-talk audio recording and communication with the backend.
 * It records audio, sends it to the STT→Claude→TTS workflow, and returns playable audio.
 */
export class VoiceService {
    private mediaRecorder: MediaRecorder | null = null
    private audioChunks: Blob[] = []
    private stream: MediaStream | null = null
    private config: Required<VoiceServiceConfig>
    
    constructor(config: VoiceServiceConfig) {
        this.config = {
            apiBase: config.apiBase,
            sampleRate: config.sampleRate || 48000,
            mimeType: config.mimeType || 'audio/webm',
        }
    }
    
    /**
     * Start recording audio from the microphone.
     */
    async startRecording(): Promise<void> {
        try {
            // Request microphone permission
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: this.config.sampleRate,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            })
            
            // Determine the best available audio format
            const mimeType = this.getBestMimeType()
            
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType,
                audioBitsPerSecond: 128000,
            })
            
            this.audioChunks = []
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data)
                }
            }
            
            this.mediaRecorder.start(100) // Collect data every 100ms
            
        } catch (error) {
            this.cleanup()
            throw new Error(
                error instanceof Error
                    ? `Microphone access failed: ${error.message}`
                    : 'Unable to access microphone'
            )
        }
    }
    
    /**
     * Stop recording and return the recorded audio blob.
     */
    async stopRecording(): Promise<Blob> {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder) {
                reject(new Error('No active recording'))
                return
            }
            
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, {
                    type: this.mediaRecorder?.mimeType || 'audio/webm',
                })
                this.cleanup()
                resolve(audioBlob)
            }
            
            this.mediaRecorder.onerror = (event: Event) => {
                const error = (event as any).error || new Error('Recording failed')
                this.cleanup()
                reject(error)
            }
            
            this.mediaRecorder.stop()
        })
    }
    
    /**
     * Send recorded audio to the backend workflow and get TTS audio response.
     */
    async sendAudioToBackend(
        audioBlob: Blob,
        options: {
            difficulty?: Difficulty
            questionContext?: string
        } = {}
    ): Promise<Blob> {
        try {
            // Convert audio blob to base64
            const base64Audio = await this.blobToBase64(audioBlob)
            
            // Determine MIME type for backend
            const mimeType = audioBlob.type || 'audio/webm'
            
            // Prepare payload for /workflow/input/stream endpoint
            const payload: any = {
                mode: 'voice',
                audio_b64: base64Audio,
                mime: mimeType,
            }
            
            if (options.difficulty) {
                payload.difficulty = options.difficulty
            }
            
            if (options.questionContext) {
                payload.question = { statement: options.questionContext }
            }
            
            // Send to backend workflow endpoint
            const response = await fetch(`${this.config.apiBase}/workflow/input/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })
            
            if (!response.ok) {
                const errorText = await response.text()
                throw new Error(`Backend error: ${errorText || response.statusText}`)
            }
            
            // The backend returns raw PCM audio - convert to playable format
            const audioData = await response.arrayBuffer()
            
            // Create a blob with the audio data
            // Note: The backend returns PCM L16 format, we'll need to wrap it properly
            const audioBlob = new Blob([audioData], {
                type: 'audio/L16;rate=48000;channels=1',
            })
            
            return audioBlob
            
        } catch (error) {
            throw new Error(
                error instanceof Error
                    ? `Failed to process audio: ${error.message}`
                    : 'Audio processing failed'
            )
        }
    }
    
    /**
     * Convert audio blob to base64 string.
     */
    private async blobToBase64(blob: Blob): Promise<string> {
        return new Promise((resolve, reject) => {
            const reader = new FileReader()
            reader.onloadend = () => {
                const base64 = reader.result as string
                // Remove data URL prefix (e.g., "data:audio/webm;base64,")
                const base64Data = base64.split(',')[1]
                resolve(base64Data)
            }
            reader.onerror = reject
            reader.readAsDataURL(blob)
        })
    }
    
    /**
     * Get the best supported MIME type for audio recording.
     */
    private getBestMimeType(): string {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
        ]
        
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type
            }
        }
        
        return 'audio/webm' // Fallback
    }
    
    /**
     * Clean up resources.
     */
    private cleanup(): void {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop())
            this.stream = null
        }
        
        this.mediaRecorder = null
        this.audioChunks = []
    }
    
    /**
     * Cancel recording without saving.
     */
    cancelRecording(): void {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop()
        }
        this.cleanup()
    }
    
    /**
     * Check if browser supports audio recording.
     */
    static isSupported(): boolean {
        return !!(
            navigator.mediaDevices &&
            navigator.mediaDevices.getUserMedia &&
            typeof MediaRecorder !== 'undefined'
        )
    }
}

/**
 * Create a playable audio URL from PCM audio blob.
 * PCM L16 needs to be wrapped in a WAV container for browser playback.
 */
export function createPCMAudioUrl(pcmBlob: Blob, sampleRate: number = 48000): string {
    // For now, create a simple object URL
    // Note: Browsers may not play raw PCM directly, might need WAV wrapper
    return URL.createObjectURL(pcmBlob)
}

/**
 * Convert PCM data to WAV format for browser playback.
 */
export async function pcmToWav(
    pcmData: ArrayBuffer,
    sampleRate: number = 48000,
    numChannels: number = 1,
    bitDepth: number = 16
): Promise<Blob> {
    const dataLength = pcmData.byteLength
    const buffer = new ArrayBuffer(44 + dataLength)
    const view = new DataView(buffer)
    
    // WAV header
    const writeString = (offset: number, string: string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i))
        }
    }
    
    writeString(0, 'RIFF')
    view.setUint32(4, 36 + dataLength, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true) // Subchunk1Size
    view.setUint16(20, 1, true) // AudioFormat (PCM)
    view.setUint16(22, numChannels, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true) // ByteRate
    view.setUint16(32, numChannels * (bitDepth / 8), true) // BlockAlign
    view.setUint16(34, bitDepth, true)
    writeString(36, 'data')
    view.setUint32(40, dataLength, true)
    
    // Copy PCM data
    const pcmView = new Uint8Array(pcmData)
    const bufferView = new Uint8Array(buffer)
    bufferView.set(pcmView, 44)
    
    return new Blob([buffer], { type: 'audio/wav' })
}

