    import { create } from 'zustand'

export interface TranscriptWord {
    word: string
    start_time: number
    end_time: number
}

export interface LiveTranscript {
    transcription: TranscriptWord[]
    last_updated: string
    word_count: number
}

export interface CaptionData {
    words: TranscriptWord[]
    status: 'active' | 'no_data' | 'error'
    last_updated: number
    word_count?: number
}

export type RecordingState = 'idle' | 'recording' | 'processing' | 'playing'

interface VoiceState {
    // Recording state
    recordingState: RecordingState
    recordingStartTime: number | null
    
    // Audio processing
    isProcessingAudio: boolean
    audioError: string | null
    
    // Live transcript
    liveTranscript: LiveTranscript | null
    transcriptError: string | null
    
    // Playback
    isPlaying: boolean
    audioUrl: string | null
    
    // Avatar sync
    avatarSpeaking: boolean
    captionData: CaptionData | null
    
    // Actions
    startRecording: () => void
    stopRecording: () => void
    setProcessing: (processing: boolean) => void
    setAudioError: (error: string | null) => void
    setLiveTranscript: (transcript: LiveTranscript | null) => void
    setTranscriptError: (error: string | null) => void
    setPlaying: (playing: boolean) => void
    setAudioUrl: (url: string | null) => void
    setAvatarSpeaking: (speaking: boolean) => void
    setCaptionData: (data: CaptionData | null) => void
    reset: () => void
}

const initialState = {
    recordingState: 'idle' as RecordingState,
    recordingStartTime: null,
    isProcessingAudio: false,
    audioError: null,
    liveTranscript: null,
    transcriptError: null,
    isPlaying: false,
    audioUrl: null,
    avatarSpeaking: false,
    captionData: null,
}

export const useVoice = create<VoiceState>((set) => ({
    ...initialState,
    
    startRecording: () => set({
        recordingState: 'recording',
        recordingStartTime: Date.now(),
        audioError: null,
    }),
    
    stopRecording: () => set((state) => ({
        recordingState: state.isProcessingAudio ? 'processing' : 'idle',
        recordingStartTime: null,
    })),
    
    setProcessing: (processing) => set({
        isProcessingAudio: processing,
        recordingState: processing ? 'processing' : 'idle',
    }),
    
    setAudioError: (error) => set({
        audioError: error,
        recordingState: 'idle',
        isProcessingAudio: false,
    }),
    
    setLiveTranscript: (transcript) => set({
        liveTranscript: transcript,
        transcriptError: null,
    }),
    
    setTranscriptError: (error) => set({
        transcriptError: error,
    }),
    
    setPlaying: (playing) => set({
        isPlaying: playing,
        recordingState: playing ? 'playing' : 'idle',
    }),
    
    setAudioUrl: (url) => set({
        audioUrl: url,
    }),
    
    setAvatarSpeaking: (speaking) => set({
        avatarSpeaking: speaking,
    }),
    
    setCaptionData: (data) => set({
        captionData: data,
    }),
    
    reset: () => set(initialState),
}))

