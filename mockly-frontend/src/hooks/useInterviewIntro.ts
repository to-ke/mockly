import { useEffect, useRef, useState } from 'react'
import { pcmToWav } from '@/services/voiceService'
import type { Difficulty } from '@/stores/app'

interface UseInterviewIntroOptions {
    apiBase: string
    difficulty: Difficulty
    questionContext: string | null
    onStart?: () => void
    onComplete?: () => void
    onError?: (error: string) => void
    onAudioReady?: (audioUrl: string, text: string) => void
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
    onAudioReady,
}: UseInterviewIntroOptions) {
    const [isPlaying, setIsPlaying] = useState(false)
    const [hasPlayed, setHasPlayed] = useState(false)
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
            
            // Buffer all PCM audio chunks with timeout
            console.log('[useInterviewIntro] Buffering audio for lipsync...')
            const audioChunks: Uint8Array[] = []
            const reader = response.body.getReader()
            let receivedBytes = 0
            let chunkCount = 0
            let lastChunkTime = Date.now()
            const TIMEOUT_MS = 5000 // 5 second timeout between chunks
            
            try {
                while (true) {
                    // Create a timeout promise
                    const timeoutPromise = new Promise<{ done: true; value?: undefined }>((resolve) => {
                        setTimeout(() => {
                            console.log('[useInterviewIntro] ⚠ Timeout waiting for next chunk, assuming stream complete')
                            resolve({ done: true })
                        }, TIMEOUT_MS)
                    })
                    
                    // Race between reading next chunk and timeout
                    const result = await Promise.race([
                        reader.read(),
                        timeoutPromise
                    ])
                    
                    const { done, value } = result
                    
                    if (done) {
                        console.log(`[useInterviewIntro] ✓ Stream complete. Total: ${receivedBytes} bytes in ${chunkCount} chunks`)
                        break
                    }
                    
                    chunkCount++
                    receivedBytes += value.byteLength
                    audioChunks.push(value)
                    lastChunkTime = Date.now()
                    
                    // Log every 10 chunks or first/last
                    if (chunkCount === 1 || chunkCount % 10 === 0) {
                        console.log(`[useInterviewIntro] Buffered chunk ${chunkCount}: ${(receivedBytes / 1024).toFixed(1)}KB total`)
                    }
                }
                
                // Cancel the reader if we timed out
                try {
                    await reader.cancel()
                } catch (e) {
                    // Ignore cancel errors
                }
                
                if (chunkCount === 0 || receivedBytes === 0) {
                    throw new Error('No audio data received from server')
                }
                
                console.log(`[useInterviewIntro] Processing ${chunkCount} chunks (${(receivedBytes / 1024).toFixed(1)}KB)...`)
                
                // Combine all chunks into a single ArrayBuffer
                console.log(`[useInterviewIntro] Combining ${chunkCount} chunks into single buffer...`)
                const totalLength = audioChunks.reduce((acc, chunk) => acc + chunk.byteLength, 0)
                const combinedPcm = new Uint8Array(totalLength)
                let offset = 0
                for (const chunk of audioChunks) {
                    combinedPcm.set(chunk, offset)
                    offset += chunk.byteLength
                }
                
                console.log(`[useInterviewIntro] Converting ${totalLength} bytes (${(totalLength / 1024).toFixed(1)}KB) to WAV...`)
                
                // Convert PCM to WAV
                const wavBlob = await pcmToWav(combinedPcm.buffer, 48000, 1, 16)
                console.log(`[useInterviewIntro] ✓ WAV blob created: ${(wavBlob.size / 1024).toFixed(1)}KB`)
                
                const audioUrl = URL.createObjectURL(wavBlob)
                console.log(`[useInterviewIntro] ✓ Audio URL created: ${audioUrl}`)
                
                // Fetch the generated text
                console.log('[useInterviewIntro] Fetching intro text...')
                const textResponse = await fetch(`${apiBase}/workflow/text/last`)
                let introText = ''
                
                if (textResponse.ok) {
                    const textData = await textResponse.json()
                    if (textData.text) {
                        introText = textData.text
                        console.log('[useInterviewIntro] ✓ Got intro text:', introText.substring(0, 100))
                    } else {
                        console.warn('[useInterviewIntro] ⚠ Text response OK but no text in data:', textData)
                    }
                } else {
                    console.error('[useInterviewIntro] ❌ Failed to fetch text:', textResponse.status, textResponse.statusText)
                }
                
                // Pass audio URL and text to parent for TalkingHead
                if (onAudioReady) {
                    if (introText) {
                        console.log('[useInterviewIntro] ✓✓✓ Ready for lipsync! Calling onAudioReady...')
                        onAudioReady(audioUrl, introText)
                    } else {
                        console.warn('[useInterviewIntro] ⚠ No text available, playing without lipsync')
                        onAudioReady(audioUrl, '')
                    }
                } else {
                    console.error('[useInterviewIntro] ❌ No onAudioReady callback provided!')
                }
                
                // Mark as played - TalkingHead will handle actual playback
                setIsPlaying(false)
                setHasPlayed(true)
                
                const totalTime = performance.now() - startTime
                console.log(`[useInterviewIntro] ✓ Total preparation time: ${(totalTime / 1000).toFixed(1)}s`)
                
                // Call onComplete after a delay to allow avatar to finish speaking
                // The actual completion will be handled by TalkingHead's onSpeakingStateChange
                setTimeout(() => {
                    onComplete?.()
                }, 100)
                
            } catch (streamError) {
                console.error('[useInterviewIntro] ❌ Streaming error:', streamError)
                console.error('[useInterviewIntro] Error stack:', streamError)
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
        }
    }, [])
    
    return {
        isPlaying,
        hasPlayed,
        playIntroduction,
    }
}

