import { Button } from '@/components/Button'
import { Play, Square, Moon, Sun, ChevronDown } from 'lucide-react'
import { useSession } from '@/stores/session'
import { useTheme } from '@/stores/theme'
import { useAppState } from '@/stores/app'


const languages = [
    { id: 'python', label: 'Python' },
    { id: 'javascript', label: 'JavaScript' },
    { id: 'typescript', label: 'TypeScript' },
    { id: 'cpp', label: 'C++' },
    { id: 'java', label: 'Java' },
] as const


interface HeaderProps {
    onRun: () => void
    onStop: () => void
    onEnd?: () => Promise<void> | void
    ending?: boolean
}


export default function Header({ onRun, onStop, onEnd, ending }: HeaderProps) {
    const { language, setLanguage, running } = useSession()
    const { theme, toggleTheme } = useTheme()
    const { difficulty, stage } = useAppState()

    return (
        <header className="page-transition h-14 border-b border-border flex items-center justify-between px-4 bg-surface backdrop-blur">
            <div className="flex items-center gap-3">
                <div className="font-semibold tracking-wide">Mockly</div>
                <span className="hidden text-xs uppercase text-muted-foreground sm:inline-flex">
                    {difficulty} difficulty
                </span>
            </div>
            <div className="flex items-center gap-2">
                <div className="relative">
                    <select
                        value={language}
                        onChange={(event) => setLanguage(event.target.value as any)}
                        aria-label="Select language"
                        className="interactive-soft h-10 appearance-none rounded-2xl border border-border bg-surface pl-3 pr-8 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/60"
                    >
                        {languages.map(({ id, label }) => (
                            <option key={id} value={id} className="bg-surface text-foreground">
                                {label}
                            </option>
                        ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                </div>
                {!running ? (
                    <Button onClick={onRun}><Play className="mr-2 h-4 w-4" />Run</Button>
                ) : (
                    <Button variant="destructive" onClick={onStop}><Square className="mr-2 h-4 w-4" />Stop</Button>
                )}
                {stage === 'interview' && onEnd && (
                    <Button
                        variant="outline"
                        className="inline-flex"
                        onClick={() => {
                            if (onEnd) void onEnd()
                        }}
                        disabled={ending}
                    >
                        {ending ? 'Ending…' : 'End Interview'}
                    </Button>
                )}
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-10 w-10 rounded-2xl p-0"
                    onClick={toggleTheme}
                    aria-label="Toggle color theme"
                >
                    {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
                </Button>
            </div>
        </header>
    )
}
