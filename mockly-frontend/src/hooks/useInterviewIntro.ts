import { useEffect, useRef, useState } from 'react'
import { PCMAudioPlayer } from '@/services/pcmAudioPlayer'
import type { Difficulty } from '@/stores/app'

interface UseInterviewIntroOptions {
    apiBase: string
    difficulty: Difficulty
    questionContext: string | null
    onStart?: () => void
    onComplete?: () => void
    onError?: (error: string) => void
}

/**
 * Hook that automatically plays the interview introduction when triggered.
 * Fetches audio from the backend workflow endpoint and plays it.
 */
export function useInterviewIntro({
    apiBase,
    difficulty,
    questionContext,
    onStart,
    onComplete,
    onError,
}: UseInterviewIntroOptions) {
    const [isPlaying, setIsPlaying] = useState(false)
    const [hasPlayed, setHasPlayed] = useState(false)
    const audioPlayerRef = useRef<PCMAudioPlayer | null>(null)
    const abortControllerRef = useRef<AbortController | null>(null)
    
    const playIntroduction = async () => {
        if (hasPlayed || isPlaying) return
        if (!questionContext) return
        
        const startTime = performance.now()
        console.log('[useInterviewIntro] Starting introduction request...')
        
        try {
            setIsPlaying(true)
            onStart?.()
            
            // Create abort controller for this request
            abortControllerRef.current = new AbortController()
            
            // Prepare payload for backend
            const payload: any = {
                text: 'BEGIN INTERVIEW',
                difficulty,
            }
            
            // Add question context if available
            if (questionContext) {
                payload.question = {
                    statement: questionContext,
                    difficulty,
                }
            }
            
            console.log('[useInterviewIntro] Sending request to:', `${apiBase}/workflow/type/stream`)
            const fetchStart = performance.now()
            
            // Fetch streaming audio response from backend
            const response = await fetch(`${apiBase}/workflow/type/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
                signal: abortControllerRef.current.signal,
            })
            
            console.log(`[useInterviewIntro] Got response in ${(performance.now() - fetchStart).toFixed(0)}ms`)
            
            if (!response.ok) {
                throw new Error(`Backend error: ${response.status} ${response.statusText}`)
            }
            
            if (!response.body) {
                throw new Error('Response body is null')
            }
            
            // Initialize audio player for progressive playback
            if (!audioPlayerRef.current) {
                audioPlayerRef.current = new PCMAudioPlayer(48000, 1)
            }
            
            const audioPlayer = audioPlayerRef.current
            console.log('[useInterviewIntro] Starting streaming playback...')
            
            // Track first audio playback
            let firstAudioPlayed = false
            
            // Set up completion handler
            audioPlayer.onComplete = () => {
                const totalTime = performance.now() - startTime
                console.log(`[useInterviewIntro] Playback ended. Total time: ${(totalTime / 1000).toFixed(1)}s`)
                setIsPlaying(false)
                setHasPlayed(true)
                onComplete?.()
            }
            
            audioPlayer.onError = (error) => {
                console.error('[useInterviewIntro] Audio player error:', error)
                setIsPlaying(false)
                onError?.(error.message)
            }
            
            // Stream audio chunks progressively
            const reader = response.body.getReader()
            let receivedBytes = 0
            let chunkCount = 0
            
            try {
                while (true) {
                    const { done, value } = await reader.read()
                    
                    if (done) {
                        console.log(`[useInterviewIntro] Stream complete. Total: ${receivedBytes} bytes in ${chunkCount} chunks`)
                        await audioPlayer.flush()
                        break
                    }
                    
                    chunkCount++
                    receivedBytes += value.byteLength
                    
                    // Log progress every 100KB
                    if (chunkCount === 1 || receivedBytes % 100000 < value.byteLength) {
                        console.log(`[useInterviewIntro] Received chunk ${chunkCount}: ${(receivedBytes / 1024).toFixed(1)}KB total`)
                    }
                    
                    // Queue audio chunk for immediate playback
                    await audioPlayer.queuePCM(value.buffer)
                    
                    if (!firstAudioPlayed) {
                        firstAudioPlayed = true
                        console.log(`[useInterviewIntro] First audio playing after ${(performance.now() - startTime).toFixed(0)}ms`)
                    }
                }
                
                console.log(`[useInterviewIntro] Audio duration: ~${(receivedBytes / (48000 * 2)).toFixed(1)}s at 48kHz mono`)
            } catch (streamError) {
                console.error('[useInterviewIntro] Streaming error:', streamError)
                throw streamError
            }
            
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                // Request was cancelled, ignore
                return
            }
            
            const message = error instanceof Error 
                ? error.message 
                : 'Failed to load introduction'
            
            console.error('Interview intro error:', error)
            setIsPlaying(false)
            onError?.(message)
        }
    }
    
    // Cleanup on unmount
    useEffect(() => {
        return () => {
            // Abort any pending requests
            if (abortControllerRef.current) {
                abortControllerRef.current.abort()
            }
            
            // Stop and cleanup audio player
            if (audioPlayerRef.current) {
                audioPlayerRef.current.stop()
                audioPlayerRef.current = null
            }
        }
    }, [])
    
    return {
        isPlaying,
        hasPlayed,
        playIntroduction,
    }
}

