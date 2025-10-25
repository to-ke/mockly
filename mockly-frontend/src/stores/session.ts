import { create } from 'zustand'
import type { Language } from '@/types/api'


interface SessionState {
    language: Language
    code: string
    codeByLanguage: Record<Language, string>
    lastPrompt: string | null
    stdout: string
    stderr: string
    running: boolean
    setLanguage: (language: Language) => void
    setCode: (code: string) => void
    setResult: (o: { stdout?: string; stderr?: string }) => void
    setRunning: (running: boolean) => void
    resetIO: () => void
    applyQuestionPrompt: (prompt: string) => void
}


const BOILERPLATE: Record<Language, string> = {
    python: 'print("Hello from Python")',
    javascript: 'console.log("Hello from JS")',
    typescript: 'const msg: string = "Hello from TS";\nconsole.log(msg);',
    cpp: '#include <bits/stdc++.h>\nusing namespace std;\nint main(){ cout<<"Hello C++"; }',
    java: 'class Main { public static void main(String[] a){ System.out.println("Hello Java"); } }',
}


const COMMENT_PREFIX: Record<Language, string> = {
    python: '#',
    javascript: '//',
    typescript: '//',
    cpp: '//',
    java: '//',
}


const LANGUAGES: Language[] = ['python', 'javascript', 'typescript', 'cpp', 'java']


const INITIAL_CODES: Record<Language, string> = { ...BOILERPLATE }


const makeCommentBlock = (language: Language, prompt: string) => {
    const prefix = COMMENT_PREFIX[language] ?? '//'
    return prompt
        .split('\n')
        .map((line) => `${prefix} ${line}`.trimEnd())
        .join('\n')
}


export const useSession = create<SessionState>((set, get) => ({
    language: 'python',
    code: INITIAL_CODES['python'],
    codeByLanguage: { ...INITIAL_CODES },
    lastPrompt: null,
    stdout: '',
    stderr: '',
    running: false,
    setLanguage: (language) => set((state) => ({
        language,
        code: state.codeByLanguage[language] ?? BOILERPLATE[language],
    })),
    setCode: (code) => set((state) => ({
        code,
        codeByLanguage: { ...state.codeByLanguage, [state.language]: code },
    })),
    setResult: ({ stdout = '', stderr = '' }) => set({ stdout, stderr }),
    setRunning: (running) => set({ running }),
    resetIO: () => set({ stdout: '', stderr: '' }),
    applyQuestionPrompt: (prompt) => {
        const state = get()
        if (state.lastPrompt === prompt) return

        const nextCodes: Record<Language, string> = { ...state.codeByLanguage }
        LANGUAGES.forEach((language) => {
            const commentBlock = makeCommentBlock(language, prompt)
            const existing = nextCodes[language] ?? BOILERPLATE[language]
            if (!existing.startsWith(commentBlock)) {
                nextCodes[language] = `${commentBlock}\n\n${existing}`
            }
        })

        set({
            codeByLanguage: nextCodes,
            code: nextCodes[state.language],
            lastPrompt: prompt,
        })
    },
}))
