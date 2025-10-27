import { useEffect, useRef, useCallback } from 'react'
import { useVoice } from '@/stores/voice'
import { VoiceService, pcmToWav } from '@/services/voiceService'
import type { Difficulty } from '@/stores/app'

interface UsePushToTalkOptions {
    apiBase: string
    key?: string
    difficulty?: Difficulty
    questionContext?: string
    enabled?: boolean
    onError?: (error: string) => void
    onSuccess?: () => void
}

/**
 * Hook for push-to-talk functionality with keyboard control.
 * Hold down the specified key (default "V") to record audio.
 */
export function usePushToTalk({
    apiBase,
    key = 'v',
    difficulty,
    questionContext,
    enabled = true,
    onError,
    onSuccess,
}: UsePushToTalkOptions) {
    const {
        recordingState,
        audioUrl,
        startRecording,
        stopRecording,
        setProcessing,
        setAudioError,
        setPlaying,
        setAudioUrl,
    } = useVoice()
    
    const voiceServiceRef = useRef<VoiceService | null>(null)
    const isKeyDownRef = useRef(false)
    
    // Initialize voice service
    useEffect(() => {
        if (!voiceServiceRef.current) {
            voiceServiceRef.current = new VoiceService({ apiBase })
        }
    }, [apiBase])
    
    // Handle recording start
    const handleStartRecording = useCallback(async () => {
        if (!enabled || !voiceServiceRef.current) return
        if (recordingState !== 'idle') return
        
        try {
            await voiceServiceRef.current.startRecording()
            startRecording()
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Failed to start recording'
            setAudioError(message)
            onError?.(message)
        }
    }, [enabled, recordingState, startRecording, setAudioError, onError])
    
    // Handle recording stop and processing
    const handleStopRecording = useCallback(async () => {
        if (!voiceServiceRef.current) return
        if (recordingState !== 'recording') return
        
        try {
            setProcessing(true)
            stopRecording()
            
            // Get recorded audio
            const audioBlob = await voiceServiceRef.current.stopRecording()
            
            // Send to backend for processing
            const responseAudio = await voiceServiceRef.current.sendAudioToBackend(
                audioBlob,
                { difficulty, questionContext }
            )
            
            // Convert PCM to WAV for playback
            // ElevenLabs outputs PCM at 16kHz
            const arrayBuffer = await responseAudio.arrayBuffer()
            const wavBlob = await pcmToWav(arrayBuffer, 16000, 1, 16)
            
            // Create audio URL for TalkingHead to play
            const audioUrl = URL.createObjectURL(wavBlob)
            setAudioUrl(audioUrl)
            setPlaying(true)
            setProcessing(false)
            
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Failed to process audio'
            setAudioError(message)
            setProcessing(false)
            onError?.(message)
        }
    }, [
        recordingState,
        difficulty,
        questionContext,
        stopRecording,
        setProcessing,
        setAudioError,
        setPlaying,
        setAudioUrl,
        onError,
        onSuccess,
    ])
    
    // Keyboard event handlers
    useEffect(() => {
        if (!enabled) return
        
        const handleKeyDown = (event: KeyboardEvent) => {
            // Ignore if user is typing in an input field
            const target = event.target as HTMLElement
            if (
                target.tagName === 'INPUT' ||
                target.tagName === 'TEXTAREA' ||
                target.isContentEditable
            ) {
                return
            }
            
            // Check if correct key and not already pressed
            if (event.key.toLowerCase() === key.toLowerCase() && !isKeyDownRef.current) {
                event.preventDefault()
                isKeyDownRef.current = true
                handleStartRecording()
            }
        }
        
        const handleKeyUp = (event: KeyboardEvent) => {
            if (event.key.toLowerCase() === key.toLowerCase() && isKeyDownRef.current) {
                event.preventDefault()
                isKeyDownRef.current = false
                handleStopRecording()
            }
        }
        
        // Prevent default behavior when key is held down
        const handleKeyPress = (event: KeyboardEvent) => {
            if (event.key.toLowerCase() === key.toLowerCase()) {
                event.preventDefault()
            }
        }
        
        window.addEventListener('keydown', handleKeyDown)
        window.addEventListener('keyup', handleKeyUp)
        window.addEventListener('keypress', handleKeyPress)
        
        return () => {
            window.removeEventListener('keydown', handleKeyDown)
            window.removeEventListener('keyup', handleKeyUp)
            window.removeEventListener('keypress', handleKeyPress)
        }
    }, [enabled, key, handleStartRecording, handleStopRecording])
    
    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (voiceServiceRef.current) {
                voiceServiceRef.current.cancelRecording()
            }
        }
    }, [])
    
    return {
        recordingState,
        isRecording: recordingState === 'recording',
        isProcessing: recordingState === 'processing',
        isPlaying: recordingState === 'playing',
        audioUrl,
        startRecording: handleStartRecording,
        stopRecording: handleStopRecording,
    }
}

