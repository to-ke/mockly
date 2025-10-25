import Editor from '@monaco-editor/react'
import { useSession } from '@/stores/session'
import { useTheme } from '@/stores/theme'


export default function EditorPane() {
    const { code, setCode, language } = useSession()
    const { theme } = useTheme()
    const monacoLang = language === 'cpp' ? 'cpp' : (language === 'java' ? 'java' : (language === 'python' ? 'python' : language))
    const editorTheme = theme === 'dark' ? 'vs-dark' : 'light'


    return (
        <div className="interactive-soft flex h-full min-h-0 flex-col rounded-3xl border border-border/30 bg-surface/60 p-2 transition-all duration-300 dark:border-transparent dark:bg-surface/80">
            <div className="flex-1 min-h-0 overflow-hidden rounded-2xl">
                <Editor
                    className="h-full"
                    height="100%"
                    defaultValue={code}
                    value={code}
                    language={monacoLang}
                    theme={editorTheme}
                    onChange={(v) => setCode(v ?? '')}
                    options={{
                        fontSize: 14,
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                        minimap: { enabled: false },
                        scrollBeyondLastLine: false,
                        smoothScrolling: true,
                        roundedSelection: true,
                        tabSize: 2,
                        wordWrap: 'on',
                        automaticLayout: true,
                    }}
                />
            </div>
        </div>
    )
}
