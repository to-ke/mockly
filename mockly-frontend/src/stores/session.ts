import { create } from 'zustand'
import type { Language } from '@/types/api'
import { Api } from '@/services/api'


interface SessionState {
    language: Language
    code: string
    codeByLanguage: Record<Language, string>
    lastPrompt: string | null
    stdout: string
    stderr: string
    running: boolean
    currentDifficulty: string | null
    setLanguage: (language: Language) => void
    setCode: (code: string) => void
    setResult: (o: { stdout?: string; stderr?: string }) => void
    setRunning: (running: boolean) => void
    resetIO: () => void
    applyQuestionPrompt: (prompt: string) => void
    applyQuestionData: (data: { prompt: string; starter_code?: string; language?: string }) => void
    refreshStarterCodeForLanguage: (language: Language) => Promise<void>
}


const BOILERPLATE: Record<Language, string> = {
    python: 'print("Hello from Python")',
    javascript: 'console.log("Hello from JS")',
    typescript: 'const msg: string = "Hello from TS";\nconsole.log(msg);',
    cpp: `#include <iostream>
using namespace std;

int main() {
    cout << "Hello C++" << endl;
    return 0;
}`,
    java: `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello Java");
    }
}`,
    perl: 'print "Hello from Perl\\n";',
    kotlin: `fun main() {
    println("Hello from Kotlin")
}`,
    c: `#include <stdio.h>

int main() {
    printf("Hello from C\\n");
    return 0;
}`,
    csharp: `using System;

class Program {
    static void Main() {
        Console.WriteLine("Hello from C#");
    }
}`,
    ruby: 'puts "Hello from Ruby"',
    go: `package main

import "fmt"

func main() {
    fmt.Println("Hello from Go")
}`,
}


const COMMENT_PREFIX: Record<Language, string> = {
    python: '#',
    javascript: '//',
    typescript: '//',
    cpp: '//',
    java: '//',
    perl: '#',
    kotlin: '//',
    c: '//',
    csharp: '//',
    ruby: '#',
    go: '//',
}


const LANGUAGES: Language[] = ['python', 'javascript', 'typescript', 'cpp', 'java', 'perl', 'kotlin', 'c', 'csharp', 'ruby', 'go']


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
    currentDifficulty: null,
    setLanguage: (language) => {
        const state = get()
        set((state) => ({
            language,
            code: state.codeByLanguage[language] ?? BOILERPLATE[language],
        }))
        
        // If we're in an interview and have a current difficulty, fetch new starter code
        if (state.currentDifficulty && state.lastPrompt) {
            get().refreshStarterCodeForLanguage(language)
        }
    },
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
    applyQuestionData: (data) => {
        const state = get()
        if (state.lastPrompt === data.prompt) return

        const { prompt, starter_code, language: suggestedLanguage, difficulty } = data
        
        // If a language is suggested and it's valid, switch to it
        const targetLanguage = suggestedLanguage && LANGUAGES.includes(suggestedLanguage as Language) 
            ? suggestedLanguage as Language 
            : state.language

        const nextCodes: Record<Language, string> = { ...state.codeByLanguage }
        
        LANGUAGES.forEach((language) => {
            const commentBlock = makeCommentBlock(language, prompt)
            let codeContent = ''
            
            // Use starter code if available and for the target language
            if (starter_code && language === targetLanguage) {
                codeContent = starter_code
            } else {
                // Use existing code or boilerplate
                codeContent = nextCodes[language] ?? BOILERPLATE[language]
            }
            
            // Add comment block if not already present
            if (!codeContent.startsWith(commentBlock)) {
                nextCodes[language] = `${commentBlock}\n\n${codeContent}`
            } else {
                nextCodes[language] = codeContent
            }
        })

        set({
            language: targetLanguage,
            codeByLanguage: nextCodes,
            code: nextCodes[targetLanguage],
            lastPrompt: prompt,
            currentDifficulty: data.difficulty || null,
        })
    },
    refreshStarterCodeForLanguage: async (language) => {
        const state = get()
        if (!state.currentDifficulty || !state.lastPrompt) return
        
        try {
            const question = await Api.fetchQuestion({ 
                difficulty: state.currentDifficulty as any, 
                language 
            })
            
            if (question?.starter_code) {
                const commentBlock = makeCommentBlock(language, state.lastPrompt)
                const newCode = `${commentBlock}\n\n${question.starter_code}`
                
                set((state) => ({
                    codeByLanguage: { ...state.codeByLanguage, [language]: newCode },
                    code: language === state.language ? newCode : state.code,
                }))
            } else {
                // If no starter code is available, use the boilerplate with comments
                const commentBlock = makeCommentBlock(language, state.lastPrompt)
                const fallbackCode = `${commentBlock}\n\n${BOILERPLATE[language]}`
                
                set((state) => ({
                    codeByLanguage: { ...state.codeByLanguage, [language]: fallbackCode },
                    code: language === state.language ? fallbackCode : state.code,
                }))
            }
        } catch (error) {
            console.error('Failed to fetch starter code for language:', error)
        }
    },
}))
