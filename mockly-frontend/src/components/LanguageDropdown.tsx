import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown, Check } from 'lucide-react'
import { useSession } from '@/stores/session'

const languages = [
    { id: 'python', label: 'Python' },
    { id: 'javascript', label: 'JavaScript' },
    { id: 'typescript', label: 'TypeScript' },
    { id: 'cpp', label: 'C++' },
    { id: 'java', label: 'Java' },
    { id: 'perl', label: 'Perl' },
    { id: 'kotlin', label: 'Kotlin' },
    { id: 'c', label: 'C' },
    { id: 'csharp', label: 'C#' },
    { id: 'ruby', label: 'Ruby' },
    { id: 'go', label: 'Go' },
] as const

export default function LanguageDropdown() {
    const { language, setLanguage } = useSession()
    const [isOpen, setIsOpen] = useState(false)
    const [buttonRect, setButtonRect] = useState<DOMRect | null>(null)

    const selectedLanguage = languages.find(lang => lang.id === language)

    const handleLanguageSelect = (languageId: string) => {
        setLanguage(languageId as any)
        setIsOpen(false)
    }

    const handleToggle = () => {
        if (!isOpen) {
            const button = document.querySelector('[data-dropdown-button]') as HTMLElement
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
                {languages.map((lang) => (
                    <div
                        key={lang.id}
                        onClick={() => {
                            handleLanguageSelect(lang.id)
                        }}
                        className={`flex w-full cursor-pointer items-center justify-between px-3 py-2 text-sm transition-colors duration-150 hover:bg-accent hover:text-accent-foreground ${
                            language === lang.id
                                ? 'bg-primary/10 text-primary'
                                : 'text-foreground'
                        }`}
                        style={{
                            cursor: 'pointer',
                            pointerEvents: 'auto'
                        }}
                    >
                        <span className="truncate">{lang.label}</span>
                        {language === lang.id && (
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
                data-dropdown-button
                onClick={handleToggle}
                className="interactive-soft flex h-10 w-32 items-center justify-between gap-2 rounded-2xl border border-border bg-surface px-3 py-2 text-sm text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-surface/80 focus:outline-none focus:ring-2 focus:ring-primary/60"
                aria-expanded={isOpen}
                aria-haspopup="listbox"
                aria-label="Select programming language"
            >
                <span className="truncate">{selectedLanguage?.label}</span>
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
