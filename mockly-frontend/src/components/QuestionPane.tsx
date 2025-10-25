import { useSession } from '@/stores/session'

export default function QuestionPane() {
    const { lastPrompt } = useSession()

    if (!lastPrompt) {
        return (
            <div className="interactive-soft flex h-full min-h-0 flex-col rounded-3xl border border-border/30 bg-surface/60 p-4 transition-all duration-300 dark:border-transparent dark:bg-surface/80">
                <div className="flex items-center gap-2 mb-4">
                    <div className="h-2 w-2 rounded-full bg-blue-500"></div>
                    <h2 className="text-lg font-semibold text-foreground">Question</h2>
                </div>
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-muted-foreground text-center">
                        No question loaded yet.<br />
                        Start an interview to see the question here.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="interactive-soft flex h-full min-h-0 flex-col rounded-3xl border border-border/30 bg-surface/60 p-4 transition-all duration-300 dark:border-transparent dark:bg-surface/80">
            <div className="flex items-center gap-2 mb-4">
                <div className="h-2 w-2 rounded-full bg-green-500"></div>
                <h2 className="text-lg font-semibold text-foreground">Question</h2>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
                <div className="prose prose-sm max-w-none text-foreground">
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">
                        {lastPrompt}
                    </div>
                </div>
            </div>
        </div>
    )
}
