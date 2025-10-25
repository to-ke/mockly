import { create } from 'zustand'

export type Difficulty = 'easy' | 'medium' | 'hard'
export type AppStage = 'landing' | 'interview' | 'feedback'

export interface FeedbackReport {
    communication: number
    codeCleanliness: number
    codeEfficiency: number
    comments: string
}


interface AppState {
    stage: AppStage
    difficulty: Difficulty
    feedback: FeedbackReport | null
    setDifficulty: (difficulty: Difficulty) => void
    startInterview: () => void
    showFeedback: (feedback: FeedbackReport) => void
    resetInterview: () => void
}


export const useAppState = create<AppState>((set) => ({
    stage: 'landing',
    difficulty: 'easy',
    feedback: null,
    setDifficulty: (difficulty) => set({ difficulty }),
    startInterview: () => set({ stage: 'interview', feedback: null }),
    showFeedback: (feedback) => set({ stage: 'feedback', feedback }),
    resetInterview: () => set({ stage: 'landing', feedback: null }),
}))
