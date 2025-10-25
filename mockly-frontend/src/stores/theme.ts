import { create } from 'zustand'

export type Theme = 'light' | 'dark'

interface ThemeState {
    theme: Theme
    toggleTheme: () => void
    setTheme: (theme: Theme) => void
}


const applyTheme = (theme: Theme) => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(theme)
    root.dataset.theme = theme
}


export const useTheme = create<ThemeState>((set) => {
    applyTheme('dark')
    return {
        theme: 'dark',
        toggleTheme: () => set((state) => {
            const next = state.theme === 'dark' ? 'light' : 'dark'
            applyTheme(next)
            return { theme: next }
        }),
        setTheme: (theme) => {
            applyTheme(theme)
            set({ theme })
        },
    }
})
