import { useState } from 'react'
import Header from '@/components/Header'
import EditorPane from '@/components/EditorPane'
import ConsolePane from '@/components/ConsolePane'
import { HorizontalResizable } from '@/components/Resizable'
import { FloatingPane } from '@/components/FloatingPane'
import { Landing } from '@/components/Landing'
import { FeedbackView } from '@/components/FeedbackView'
import { Api } from '@/services/api'
import { useSession } from '@/stores/session'
import { useAppState } from '@/stores/app'


export default function App() {
  const { stage, showFeedback, difficulty } = useAppState()
  const { language, code, setResult, running, setRunning, resetIO, lastPrompt } = useSession()
  const [ending, setEnding] = useState(false)
  const [endError, setEndError] = useState<string | null>(null)


  const run = async () => {
    if (running) return
    setRunning(true)
    resetIO()
    try {
      const res = await Api.execute({ language, source: code, timeoutMs: 4000 })
      setResult({ stdout: res.stdout, stderr: res.stderr })
    } catch (err: unknown) {
      if (err instanceof Error) {
        setResult({ stdout: '', stderr: err.message })
      } else {
        setResult({ stdout: '', stderr: String(err) })
      }
    } finally {
      setRunning(false)
    }
  }


  const stop = () => {
    // In mock mode this just cancels UI state; with FastAPI you might cancel a job id
    setRunning(false)
  }


  const endInterview = async () => {
    if (ending) return
    setEndError(null)
    setEnding(true)
    try {
      setRunning(false)
      
      // Prepare question context for evaluation
      const question = lastPrompt ? {
        prompt: lastPrompt,
        difficulty: difficulty,
      } : undefined
      
      // Fetch feedback with code, language, and question context
      const report = await Api.fetchFeedback({
        code,
        language,
        question,
      })
      showFeedback(report)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setEndError(err.message)
      } else {
        setEndError(String(err))
      }
    } finally {
      setEnding(false)
    }
  }


  if (stage === 'landing') {
    return <Landing />
  }

  if (stage === 'feedback') {
    return <FeedbackView />
  }


  return (
    <div className="flex h-full flex-col">
      <Header onRun={run} onStop={stop} onEnd={endInterview} ending={ending} />
      <main className="page-transition flex-1 p-3 overflow-hidden min-h-0">
        {endError && (
          <div className="mb-3 rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {endError}
          </div>
        )}
        <HorizontalResizable
          left={<EditorPane />}
          right={<ConsolePane />}
        />
      </main>
      <FloatingPane />
    </div>
  )
}
