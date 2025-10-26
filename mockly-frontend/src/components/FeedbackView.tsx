import { Button } from '@/components/Button'
import { useAppState } from '@/stores/app'
import { Star } from 'lucide-react'
import { renderMarkdown } from '@/lib/markdown'


interface RatingCardProps {
    label: string
    score: number
}


const RatingCard = ({ label, score }: RatingCardProps) => {
    const stars = Array.from({ length: 5 }, (_v, index) => index < score)
    return (
        <div className="flex flex-col items-center gap-3 rounded-3xl border border-border/60 bg-surface/80 px-4 py-6 text-center shadow-sm dark:border-transparent dark:bg-surface/60 dark:shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
            <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
            <div className="flex items-center gap-1">
                {stars.map((active, index) => (
                    <Star
                        key={index}
                        className={`h-5 w-5 transition-colors ${active ? 'fill-primary text-primary drop-shadow-sm' : 'text-border'}`}
                    />
                ))}
            </div>
            <span className="text-xs font-medium text-muted-foreground/80">{score} / 5</span>
        </div>
    )
}


export function FeedbackView() {
    const { feedback, resetInterview } = useAppState()

    if (!feedback) {
        return (
            <div className="flex h-full flex-col items-center justify-center gap-4">
                <p className="text-muted-foreground">Loading feedback...</p>
                <Button onClick={resetInterview}>Return home</Button>
            </div>
        )
    }

    return (
        <div className="page-transition flex h-full items-center justify-center bg-background px-6 py-12 text-foreground">
            <div className="card-rise w-full max-w-3xl space-y-8 rounded-3xl border border-border/60 bg-surface/90 p-8 shadow-2xl backdrop-blur dark:border-transparent dark:bg-surface/80 dark:shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
                <header className="space-y-2 text-center">
                    <p className="text-xs uppercase tracking-widest text-muted-foreground">Interview Feedback</p>
                    <h1 className="text-4xl font-semibold">Great work!</h1>
                    <p className="text-sm text-muted-foreground">
                        Here&apos;s a quick snapshot of how you performed across key categories.
                    </p>
                </header>

                <section className="grid gap-4 sm:grid-cols-3">
                    <RatingCard label="Communication" score={feedback.communication} />
                    <RatingCard label="Code Cleanliness" score={feedback.codeCleanliness} />
                    <RatingCard label="Code Efficiency" score={feedback.codeEfficiency} />
                </section>

                <section className="space-y-3">
                    <h2 className="text-base font-semibold text-foreground">Interviewer Comments</h2>
                    <div 
                        className="card-rise delay-100 max-h-60 overflow-y-auto rounded-3xl border border-border/60 bg-background/80 p-5 text-sm leading-relaxed text-muted-foreground dark:border-transparent dark:bg-background/40 dark:shadow-[0_0_0_1px_rgba(255,255,255,0.08)] [&>p]:mb-3 [&>p:last-child]:mb-0 [&_strong]:text-foreground [&_strong]:font-semibold [&_strong]:text-base [&_strong]:block [&_strong]:mb-2 [&_strong]:mt-4 [&_strong:first-child]:mt-0 [&_em]:italic [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:bg-muted/50 [&_code]:text-foreground/90 [&_code]:font-mono [&_code]:text-xs"
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(feedback.comments) }}
                    />
                </section>

                <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
                    <Button variant="outline" onClick={resetInterview}>
                        Back to Home
                    </Button>
                </div>
            </div>
        </div>
    )
}
