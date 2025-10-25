import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown, Check } from 'lucide-react'
import { useAppState, type Difficulty } from '@/stores/app'

const difficultyOptions: Array<{ value: Difficulty; label: string }> = [
    { value: 'easy', label: 'Easy' },
    { value: 'medium', label: 'Medium' },
    { value: 'hard', label: 'Hard' },
]

export default function DifficultyDropdown() {
    const { difficulty, setDifficulty } = useAppState()
    const [isOpen, setIsOpen] = useState(false)
    const [buttonRect, setButtonRect] = useState<DOMRect | null>(null)

    const selectedDifficulty = difficultyOptions.find(diff => diff.value === difficulty)

    const handleDifficultySelect = (difficultyValue: Difficulty) => {
        setDifficulty(difficultyValue)
        setIsOpen(false)
    }

    const handleToggle = () => {
        if (!isOpen) {
            const button = document.querySelector('[data-difficulty-dropdown-button]') as HTMLElement
            if (button) {
                setButtonRect(button.getBoundingClientRect())
            }
        }
        setIsOpen(!isOpen)
    }

    const dropdownContent = isOpen && (
        <div 
            className="fixed z-[99999] overflow-hidden rounded-2xl border border-border bg-surface shadow-lg"
            style={{ 
                position: 'fixed',
                top: buttonRect ? buttonRect.bottom + 4 : 0,
                left: buttonRect ? buttonRect.left : 0,
                width: buttonRect ? buttonRect.width : 160,
                zIndex: 99999,
                pointerEvents: 'auto'
            }}
        >
            <div className="py-1">
                {difficultyOptions.map((option) => (
                    <div
                        key={option.value}
                        onClick={() => {
                            handleDifficultySelect(option.value)
                        }}
                        className={`flex w-full cursor-pointer items-center justify-between px-3 py-2 text-sm transition-colors duration-150 hover:bg-accent hover:text-accent-foreground ${
                            difficulty === option.value
                                ? 'bg-primary/10 text-primary'
                                : 'text-foreground'
                        }`}
                        style={{
                            cursor: 'pointer',
                            pointerEvents: 'auto'
                        }}
                    >
                        <span className="truncate">{option.label}</span>
                        {difficulty === option.value && (
                            <Check className="h-4 w-4 text-primary" />
                        )}
                    </div>
                ))}
            </div>
        </div>
    )

    return (
        <div className="relative">
            <button
                data-difficulty-dropdown-button
                onClick={handleToggle}
                className="interactive-soft flex h-11 w-32 items-center justify-between gap-2 rounded-2xl border border-border bg-background px-3 py-2 text-sm text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-background/80 focus:outline-none focus:ring-2 focus:ring-primary/60"
                aria-expanded={isOpen}
                aria-haspopup="listbox"
                aria-label="Select question difficulty"
            >
                <span className="truncate">{selectedDifficulty?.label}</span>
                <ChevronDown 
                    className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${
                        isOpen ? 'rotate-180' : ''
                    }`} 
                />
            </button>

            {isOpen && createPortal(dropdownContent, document.body)}
        </div>
    )
}
