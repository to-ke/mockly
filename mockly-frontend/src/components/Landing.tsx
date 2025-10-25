import { useState } from 'react'
import { Button } from '@/components/Button'
import DifficultyDropdown from '@/components/DifficultyDropdown'
import { useAppState } from '@/stores/app'
import { Api } from '@/services/api'
import { useSession } from '@/stores/session'


export function Landing() {
    const { difficulty, startInterview } = useAppState()
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
                <div className="mb-4 text-center">
                    <label className="block text-sm font-medium text-muted-foreground">
                        Select question difficulty
                    </label>
                    <div className="mt-2 flex justify-center">
                        <DifficultyDropdown />
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
