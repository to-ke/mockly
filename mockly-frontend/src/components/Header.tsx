import { Button } from '@/components/Button'
import LanguageDropdown from '@/components/LanguageDropdown'
import { Play, Square, Moon, Sun } from 'lucide-react'
import { useSession } from '@/stores/session'
import { useTheme } from '@/stores/theme'
import { useAppState } from '@/stores/app'


interface HeaderProps {
    onRun: () => void
    onStop: () => void
    onEnd?: () => Promise<void> | void
    ending?: boolean
}


export default function Header({ onRun, onStop, onEnd, ending }: HeaderProps) {
    const { running } = useSession()
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
                <LanguageDropdown />
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
