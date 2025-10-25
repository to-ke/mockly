import { useState } from 'react'
import { Button } from '@/components/Button'
import { useAppState, type Difficulty } from '@/stores/app'
import { Api } from '@/services/api'
import { useSession } from '@/stores/session'


const difficultyOptions: Array<{ value: Difficulty; label: string }> = [
    { value: 'easy', label: 'Easy' },
    { value: 'medium', label: 'Medium' },
    { value: 'hard', label: 'Hard' },
]


export function Landing() {
    const { difficulty, setDifficulty, startInterview } = useAppState()
    const { applyQuestionPrompt } = useSession()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)


    const handleStart = async () => {
        setError(null)
        setLoading(true)
        try {
            // Placeholder request for later backend integration
            const question = await Api.fetchQuestion({ difficulty })
            if (question?.prompt) {
                applyQuestionPrompt(question.prompt)
            }
            startInterview()
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message)
            } else {
                setError(String(err))
            }
        } finally {
            setLoading(false)
        }
    }


    return (
        <div className="page-transition flex h-full flex-col items-center justify-center gap-10 bg-background px-6 text-foreground">
            <header className="card-rise text-center">
                <h1 className="text-5xl font-bold tracking-tight">Mockly</h1>
                <p className="mt-3 max-w-md text-base text-muted-foreground">
                    Practice coding interviews with realistic prompts and instant feedback.
                </p>
            </header>
            <section className="card-rise delay-100 w-full max-w-md rounded-3xl border border-border bg-surface/70 p-6 shadow-xl backdrop-blur">
                <div className="mb-4">
                    <label htmlFor="difficulty" className="block text-sm font-medium text-muted-foreground">
                        Select question difficulty
                    </label>
                    <div className="relative mt-2">
                        <select
                            id="difficulty"
                            value={difficulty}
                            onChange={(event) => setDifficulty(event.target.value as Difficulty)}
                            className="interactive-soft h-11 w-full appearance-none rounded-2xl border border-border bg-background pl-3 pr-10 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
                        >
                            {difficultyOptions.map(({ value, label }) => (
                                <option key={value} value={value}>
                                    {label}
                                </option>
                            ))}
                        </select>
                        <svg
                            className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            aria-hidden="true"
                        >
                            <path
                                fillRule="evenodd"
                                d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
                                clipRule="evenodd"
                            />
                        </svg>
                    </div>
                </div>
                <Button onClick={handleStart} className="interactive-soft w-full" disabled={loading}>
                    {loading ? 'Preparing interview…' : 'Start Interview'}
                </Button>
                {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
            </section>
        </div>
    )
}
