import { useSession } from '@/stores/session'


export default function ConsolePane() {
    const { stdout, stderr } = useSession()
    const hasError = Boolean(stderr?.trim())
    return (
        <div className="interactive-soft flex h-full min-h-0 flex-col rounded-3xl border border-border/30 bg-surface/60 p-3 transition-all duration-300 dark:border-transparent dark:bg-surface/80">
            <div className="flex-1 overflow-auto rounded-2xl border border-border/40 bg-background/30 p-4 backdrop-blur dark:border-transparent dark:bg-background/40">
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Output</div>
                <pre className="text-sm whitespace-pre-wrap leading-relaxed">{stdout || '—'}</pre>
                {hasError && (
                    <pre className="mt-4 text-sm whitespace-pre-wrap leading-relaxed text-destructive">{stderr}</pre>
                )}
            </div>
        </div>
    )
}
