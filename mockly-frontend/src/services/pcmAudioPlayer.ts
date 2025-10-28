/**
 * Progressive PCM Audio Player
 * 
 * Plays PCM audio chunks as they arrive using the Web Audio API.
 * Provides low-latency streaming playback without waiting for entire audio file.
 */

export class PCMAudioPlayer {
    private audioContext: AudioContext | null = null
    private sampleRate: number
    private channels: number
    private nextStartTime: number = 0
    private isPlaying: boolean = false
    private scheduledBuffers: AudioBufferSourceNode[] = []
    private partialBuffer: Uint8Array = new Uint8Array(0)
    private totalQueuedBytes: number = 0
    private hasStartedPlayback: boolean = false
    private minBufferBytes: number = 192000 // Increased to ~2s at 48kHz mono for smoother playback
    private bufferAheadTime: number = 0.5 // Keep 0.5s of audio scheduled ahead
    
    public onComplete: (() => void) | null = null
    public onError: ((error: Error) => void) | null = null
    
    constructor(sampleRate: number = 48000, channels: number = 1) {
        this.sampleRate = sampleRate
        this.channels = channels
        // Larger initial buffer: 2 seconds at 48kHz mono (48000 * 1 * 2 * 2 bytes)
        this.minBufferBytes = Math.floor((sampleRate * channels * 2 * 2.0) / 2) * 2 // Ensure even
    }
    
    /**
     * Initialize the audio context (requires user interaction)
     */
    private async ensureAudioContext(): Promise<AudioContext> {
        if (!this.audioContext) {
            this.audioContext = new AudioContext({ sampleRate: this.sampleRate })
            this.nextStartTime = this.audioContext.currentTime
        }
        
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume()
        }
        
        return this.audioContext
    }
    
    /**
     * Queue a PCM audio chunk for playback
     * Handles byte alignment and initial buffering
     * 
     * @param pcmData - ArrayBuffer containing 16-bit PCM audio
     */
    async queuePCM(pcmData: ArrayBuffer): Promise<void> {
        try {
            // Combine with any partial buffer from previous chunk
            const newData = new Uint8Array(pcmData)
            const combined = new Uint8Array(this.partialBuffer.length + newData.length)
            combined.set(this.partialBuffer, 0)
            combined.set(newData, this.partialBuffer.length)
            
            // Ensure we have an even number of bytes for Int16Array
            const evenLength = Math.floor(combined.length / 2) * 2
            
            if (evenLength === 0) {
                // Not enough data yet, buffer it
                this.partialBuffer = combined
                return
            }
            
            // Extract aligned data for processing
            const alignedData = combined.slice(0, evenLength)
            
            // Store any remaining partial byte
            if (evenLength < combined.length) {
                this.partialBuffer = combined.slice(evenLength)
            } else {
                this.partialBuffer = new Uint8Array(0)
            }
            
            this.totalQueuedBytes += alignedData.length
            
            // Initial buffering to prevent choppy playback
            if (!this.hasStartedPlayback && this.totalQueuedBytes < this.minBufferBytes) {
                console.log(`[PCMAudioPlayer] Buffering... ${this.totalQueuedBytes}/${this.minBufferBytes} bytes`)
                // Store aligned data temporarily
                const temp = new Uint8Array(this.partialBuffer.length + alignedData.length)
                temp.set(alignedData, 0)
                temp.set(this.partialBuffer, alignedData.length)
                this.partialBuffer = temp
                return
            }
            
            // On first playback, process everything we've buffered
            if (!this.hasStartedPlayback) {
                this.hasStartedPlayback = true
                console.log(`[PCMAudioPlayer] Starting playback with ${this.totalQueuedBytes} bytes buffered`)
            }
            
            const audioContext = await this.ensureAudioContext()
            
            // Convert PCM Int16 to Float32 for Web Audio API
            const pcmView = new Int16Array(alignedData.buffer, alignedData.byteOffset, alignedData.byteLength / 2)
            const audioBuffer = audioContext.createBuffer(
                this.channels,
                pcmView.length / this.channels,
                this.sampleRate
            )
            
            // Copy and convert PCM data
            for (let channel = 0; channel < this.channels; channel++) {
                const channelData = audioBuffer.getChannelData(channel)
                for (let i = 0; i < channelData.length; i++) {
                    const sampleIndex = i * this.channels + channel
                    channelData[i] = pcmView[sampleIndex] / 32768.0 // Convert to [-1, 1]
                }
            }
            
            // Schedule playback
            const source = audioContext.createBufferSource()
            source.buffer = audioBuffer
            source.connect(audioContext.destination)
            
            // Ensure smooth scheduling with buffer ahead time
            const now = audioContext.currentTime
            const startTime = Math.max(now + this.bufferAheadTime, this.nextStartTime)
            
            source.start(startTime)
            this.nextStartTime = startTime + audioBuffer.duration
            
            // Log scheduling info for debugging gaps
            const bufferAhead = this.nextStartTime - now
            if (bufferAhead < 0.1) {
                console.warn(`[PCMAudioPlayer] Low buffer: only ${bufferAhead.toFixed(3)}s ahead`)
            }
            
            // Track scheduled buffers
            this.scheduledBuffers.push(source)
            
            // Cleanup after playback
            source.onended = () => {
                const index = this.scheduledBuffers.indexOf(source)
                if (index > -1) {
                    this.scheduledBuffers.splice(index, 1)
                }
                
                // If no more buffers are scheduled, we might be done
                if (this.scheduledBuffers.length === 0 && !this.isPlaying) {
                    this.onComplete?.()
                }
            }
            
            if (!this.isPlaying) {
                this.isPlaying = true
            }
            
        } catch (error) {
            console.error('[PCMAudioPlayer] Error queuing audio:', error)
            this.onError?.(error instanceof Error ? error : new Error(String(error)))
        }
    }
    
    /**
     * Signal that no more audio chunks will be added
     * Process any remaining buffered data
     */
    async flush(): Promise<void> {
        // Process any remaining partial buffer
        if (this.partialBuffer.length >= 2) {
            const evenLength = Math.floor(this.partialBuffer.length / 2) * 2
            const finalData = this.partialBuffer.slice(0, evenLength)
            
            if (finalData.length > 0) {
                console.log(`[PCMAudioPlayer] Flushing ${finalData.length} remaining bytes`)
                
                const audioContext = await this.ensureAudioContext()
                const pcmView = new Int16Array(finalData.buffer, finalData.byteOffset, finalData.byteLength / 2)
                const audioBuffer = audioContext.createBuffer(
                    this.channels,
                    pcmView.length / this.channels,
                    this.sampleRate
                )
                
                for (let channel = 0; channel < this.channels; channel++) {
                    const channelData = audioBuffer.getChannelData(channel)
                    for (let i = 0; i < channelData.length; i++) {
                        const sampleIndex = i * this.channels + channel
                        channelData[i] = pcmView[sampleIndex] / 32768.0
                    }
                }
                
                const source = audioContext.createBufferSource()
                source.buffer = audioBuffer
                source.connect(audioContext.destination)
                
                const now = audioContext.currentTime
                const startTime = Math.max(now, this.nextStartTime)
                source.start(startTime)
                
                this.scheduledBuffers.push(source)
                source.onended = () => {
                    const index = this.scheduledBuffers.indexOf(source)
                    if (index > -1) {
                        this.scheduledBuffers.splice(index, 1)
                    }
                    if (this.scheduledBuffers.length === 0) {
                        this.onComplete?.()
                    }
                }
            }
        }
        
        this.isPlaying = false
        this.partialBuffer = new Uint8Array(0)
        
        // If no buffers are scheduled, complete immediately
        if (this.scheduledBuffers.length === 0) {
            this.onComplete?.()
        }
    }
    
    /**
     * Stop playback and cleanup resources
     */
    stop(): void {
        // Stop all scheduled buffers
        for (const source of this.scheduledBuffers) {
            try {
                source.stop()
            } catch (e) {
                // Already stopped or not started
            }
        }
        this.scheduledBuffers = []
        
        // Close audio context
        if (this.audioContext) {
            this.audioContext.close()
            this.audioContext = null
        }
        
        this.isPlaying = false
        this.nextStartTime = 0
        this.partialBuffer = new Uint8Array(0)
        this.totalQueuedBytes = 0
        this.hasStartedPlayback = false
    }
    
    /**
     * Get current playback state
     */
    get playing(): boolean {
        return this.isPlaying || this.scheduledBuffers.length > 0
    }
}

