import { useCallback, useEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, Mic, MicOff, Send, Radio } from 'lucide-react'
import { Button } from '@/components/Button'
import { cn } from '@/lib/cn'
import { AudioStreamer } from '@/services/audioStreamer'
import { resolveBackendBase } from '@/services/api'
import { TalkingHead } from '@/components/TalkingHead'
import { LiveTranscript } from '@/components/LiveTranscript'
import { useSession } from '@/stores/session'
import { useAppState } from '@/stores/app'
import { useVoice } from '@/stores/voice'
import { usePushToTalk } from '@/hooks/usePushToTalk'
import { useInterviewIntro } from '@/hooks/useInterviewIntro'
import renderMarkdown from '@/lib/markdown'


type ChatMessage = {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: number
}


const initialMessages: ChatMessage[] = [
    {
        id: 'welcome',
        role: 'assistant',
        content: 'Hi there! I can help you with your interview. Enable push-to-talk (PTT) and hold V to speak!',
        timestamp: Date.now(),
    },
]


const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)


export function FloatingPane() {
    const [position, setPosition] = useState({ x: 32, y: 120 })
    const [isDragging, setIsDragging] = useState(false)
    const [chatOpen, setChatOpen] = useState(false)
    const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
    const [draft, setDraft] = useState('')
    const paneRef = useRef<HTMLDivElement | null>(null)
    const dragOffsetRef = useRef({ x: 0, y: 0 })
    const chatBodyRef = useRef<HTMLDivElement | null>(null)
    const pendingReplyTimeouts = useRef<number[]>([])
    const audioStreamerRef = useRef<AudioStreamer | null>(null)
    const [micMuted, setMicMuted] = useState(true)
    const [micBusy, setMicBusy] = useState(false)
    const [micError, setMicError] = useState<string | null>(null)
    
    // Voice and transcription state
    const { difficulty, stage } = useAppState()
    const { lastPrompt } = useSession()
    const { recordingState, audioError, audioUrl: voiceAudioUrl } = useVoice()
    const [pushToTalkEnabled, setPushToTalkEnabled] = useState(false)
    const [transcriptExpanded, setTranscriptExpanded] = useState(false)
    
    // State for TalkingHead lipsync
    const [currentText, setCurrentText] = useState<string | null>(null)
    const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null)
    const [avatarSpeaking, setAvatarSpeaking] = useState(false)
    const lastFetchedTimestamp = useRef<number>(0)
    
    const apiBase = resolveBackendBase()
    
    // Automatic interview introduction
    const { isPlaying: isPlayingIntro, hasPlayed: hasPlayedIntro, playIntroduction } = useInterviewIntro({
        apiBase,
        difficulty,
        questionContext: lastPrompt,
        onStart: () => {
            setMessages((prev) => [
                ...prev,
                {
                    id: `intro-start-${Date.now()}`,
                    role: 'assistant',
                    content: '🎙️ Starting interview...',
                    timestamp: Date.now(),
                },
            ])
        },
        onComplete: () => {
            setMessages((prev) => [
                ...prev,
                {
                    id: `intro-complete-${Date.now()}`,
                    role: 'assistant',
                    content: 'Ready to help! You can ask questions or start coding. Enable PTT to use voice.',
                    timestamp: Date.now(),
                },
            ])
            // Clear audio and text after completion
            setCurrentText(null)
            setCurrentAudioUrl(null)
        },
        onError: (error) => {
            setMessages((prev) => [
                ...prev,
                {
                    id: `intro-error-${Date.now()}`,
                    role: 'assistant',
                    content: `⚠️ Couldn't play introduction: ${error}. You can still chat or use PTT.`,
                    timestamp: Date.now(),
                },
            ])
        },
        onAudioReady: (audioUrl, text) => {
            console.log('[FloatingPane] ✓ Intro ready for lipsync:', {
                audioUrl: audioUrl.substring(0, 50),
                textLength: text.length
            })
            setCurrentAudioUrl(audioUrl)
            setCurrentText(text)
        },
    })
    
    // Trigger introduction when interview starts and question is loaded
    useEffect(() => {
        if (stage === 'interview' && lastPrompt && !hasPlayedIntro && !isPlayingIntro) {
            // Minimal delay to ensure UI is ready (reduced from 500ms)
            const timer = setTimeout(() => {
                console.log('[FloatingPane] Triggering introduction for:', lastPrompt.substring(0, 50))
                playIntroduction()
            }, 100)
            
            return () => clearTimeout(timer)
        }
    }, [stage, lastPrompt, hasPlayedIntro, isPlayingIntro, playIntroduction])
    
    // Fetch text and set audio URL for TalkingHead lipsync when audio becomes available
    useEffect(() => {
        if (!voiceAudioUrl) {
            console.log('[FloatingPane] No audioUrl, clearing lipsync state')
            setCurrentText(null)
            setCurrentAudioUrl(null)
            return
        }
        
        console.log('[FloatingPane] audioUrl changed, fetching text for lipsync...', {
            audioUrl: voiceAudioUrl.substring(0, 50)
        })
        
        let cancelled = false
        
        const fetchTextAndSetAudio = async () => {
            try {
                // Wait a tiny bit to ensure backend has stored the text
                await new Promise(resolve => setTimeout(resolve, 100))
                
                const response = await fetch(`${apiBase}/workflow/text/last`)
                if (!response.ok) {
                    console.error('[FloatingPane] Failed to fetch text:', response.status, response.statusText)
                    // Still play audio without lipsync
                    if (!cancelled) {
                        setCurrentAudioUrl(voiceAudioUrl)
                        setCurrentText('')
                    }
                    return
                }
                
                const data = await response.json()
                
                if (cancelled) return
                
                // Check if this is newer than what we last fetched
                if (data.timestamp <= lastFetchedTimestamp.current) {
                    console.warn('[FloatingPane] Received stale text, ignoring', {
                        receivedTimestamp: data.timestamp,
                        lastFetched: lastFetchedTimestamp.current
                    })
                    return
                }
                
                lastFetchedTimestamp.current = data.timestamp
                
                if (data.text) {
                    console.log('[FloatingPane] ✓ Got text for lipsync:', {
                        textPreview: data.text.substring(0, 100),
                        textLength: data.text.length,
                        timestamp: data.timestamp
                    })
                    setCurrentText(data.text)
                    setCurrentAudioUrl(voiceAudioUrl)
                } else {
                    console.warn('[FloatingPane] No text in response:', data)
                    // Still play audio without lipsync
                    setCurrentAudioUrl(voiceAudioUrl)
                    setCurrentText('')
                }
            } catch (error) {
                console.error('[FloatingPane] Failed to fetch text:', error)
                // Still play audio without lipsync
                if (!cancelled) {
                    setCurrentAudioUrl(voiceAudioUrl)
                    setCurrentText('')
                }
            }
        }
        
        fetchTextAndSetAudio()
        
        return () => {
            cancelled = true
        }
    }, [voiceAudioUrl, apiBase])
    
    // Push-to-talk functionality
    const { isRecording, isProcessing, isPlaying } = usePushToTalk({
        apiBase,
        key: 'v',
        difficulty,
        questionContext: lastPrompt || undefined,
        enabled: pushToTalkEnabled && !isPlayingIntro, // Disable PTT during intro
        onError: (error) => {
            setMessages((prev) => [
                ...prev,
                {
                    id: `error-${Date.now()}`,
                    role: 'assistant',
                    content: `⚠️ ${error}`,
                    timestamp: Date.now(),
                },
            ])
        },
        onSuccess: () => {
            // Could add success feedback here
        },
    })
    
    const ensureAudioStreamer = useCallback(() => {
        if (!audioStreamerRef.current) {
            audioStreamerRef.current = new AudioStreamer()
        }
        return audioStreamerRef.current
    }, [])


    const handlePointerMove = useCallback((event: PointerEvent) => {
        if (!paneRef.current) return
        if (typeof window === 'undefined') return
        const { width, height } = paneRef.current.getBoundingClientRect()
        const maxX = window.innerWidth - width - 16
        const maxY = window.innerHeight - height - 16
        const nextX = clamp(event.clientX - dragOffsetRef.current.x, 16, Math.max(maxX, 16))
        const nextY = clamp(event.clientY - dragOffsetRef.current.y, 16, Math.max(maxY, 16))
        setPosition({ x: nextX, y: nextY })
    }, [])


    const handlePointerUp = useCallback(() => {
        setIsDragging(false)
        window.removeEventListener('pointermove', handlePointerMove)
        window.removeEventListener('pointerup', handlePointerUp)
    }, [handlePointerMove])


    const handlePointerDown = useCallback(
        (event: React.PointerEvent<HTMLDivElement>) => {
            const interactiveTarget = (event.target as HTMLElement).closest('button, a, select, input, textarea')
            if (interactiveTarget) return
            if (!paneRef.current) return
            event.preventDefault()
            setIsDragging(true)
            dragOffsetRef.current = {
                x: event.clientX - position.x,
                y: event.clientY - position.y,
            }
            window.addEventListener('pointermove', handlePointerMove)
            window.addEventListener('pointerup', handlePointerUp)
        },
        [handlePointerMove, handlePointerUp, position.x, position.y]
    )


    useEffect(() => {
        return () => {
            window.removeEventListener('pointermove', handlePointerMove)
            window.removeEventListener('pointerup', handlePointerUp)
            pendingReplyTimeouts.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
            pendingReplyTimeouts.current = []
        }
    }, [handlePointerMove, handlePointerUp])


    useEffect(() => {
        if (!chatBodyRef.current) return
        chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight
    }, [messages, chatOpen])


    const handleSendMessage = (event: React.FormEvent) => {
        event.preventDefault()
        const trimmed = draft.trim()
        if (!trimmed) return

        const message: ChatMessage = {
            id: `user-${Date.now()}-${Math.random().toString(16).slice(2)}`,
            role: 'user',
            content: trimmed,
            timestamp: Date.now(),
        }
        setMessages((prev) => [...prev, message])
        setDraft('');

        // Replace canned reply with a real backend call to the assistant
        // (expects the workflow/api.py app to be mounted at /assistant).
        (async () => {
            try {
                // Include the active question so the assistant matches the editor prompt
                const state = (useSession as any).getState?.() || {}
                const qPrompt = (state.lastPrompt || '').trim()
                const qDiff = state.currentDifficulty || null
                const questionPayload = qPrompt ? { question: { statement: qPrompt, difficulty: qDiff || undefined } } : {}

                const res = await fetch('/assistant/debug/claude/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: trimmed, ...questionPayload }),
                })

                if (!res.ok) {
                    const body = await res.text()
                    throw new Error(body || res.statusText)
                }

                // Read full text response (the endpoint streams plaintext)
                const text = await res.text()
                setMessages((prev) => [
                    ...prev,
                    {
                        id: `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                        role: 'assistant',
                        content: text || "(no reply)",
                        timestamp: Date.now(),
                    },
                ])
            } catch (err) {
                const msg = err instanceof Error ? err.message : String(err)
                setMessages((prev) => [
                    ...prev,
                    {
                        id: `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                        role: 'assistant',
                        content: `Error: ${msg}`,
                        timestamp: Date.now(),
                    },
                ])
            }
        })()
    }


    useEffect(() => {
        let cancelled = false
        const streamer = ensureAudioStreamer()
        setMicBusy(true)
        streamer
            .warmup({ muted: true })
            .then(() => {
                if (!cancelled) {
                    setMicMuted(true)
                }
            })
            .catch((error) => {
                if (cancelled) return
                const message = error instanceof Error ? error.message : 'Unable to access the microphone.'
                setMicError(message)
            })
            .finally(() => {
                if (!cancelled) {
                    setMicBusy(false)
                }
            })
        return () => {
            cancelled = true
            audioStreamerRef.current
                ?.stop()
                .catch((error) => console.warn('Failed to stop audio streamer on unmount', error))
            audioStreamerRef.current = null
        }
    }, [ensureAudioStreamer])


    const handleToggleMute = async (event?: React.MouseEvent) => {
        event?.stopPropagation()
        setMicError(null)
        setMicBusy(true)
        try {
            if (micMuted) {
                await ensureAudioStreamer().setMuted(false)
                setMicMuted(false)
            } else {
                await audioStreamerRef.current?.setMuted(true)
                setMicMuted(true)
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unable to toggle the microphone.'
            setMicError(message)
            setMicMuted(true)
        } finally {
            setMicBusy(false)
        }
    }


    const statusMessage = micError || audioError
    const pushToTalkActive = isRecording || isProcessing || isPlaying || isPlayingIntro


    return (
        <div
            ref={paneRef}
            className="fixed z-50 w-80 max-w-full"
            style={{ transform: `translate3d(${position.x}px, ${position.y}px, 0)` }}
        >
            <div className="floating-pop-panel flex flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-2xl">
            <div
                className={cn(
                    'flex select-none items-center justify-between gap-2 border-b border-border px-3 py-2',
                    'cursor-grab active:cursor-grabbing',
                    isDragging && 'cursor-grabbing'
                )}
                onPointerDown={handlePointerDown}
            >
                <span className="text-sm font-semibold text-foreground">Kevin (Interviewer)</span>
                <div className="flex items-center gap-2">
                    <Button
                        variant={pushToTalkEnabled ? 'default' : 'outline'}
                        size="sm"
                        className="h-8 px-3 text-xs"
                        onClick={(e) => {
                            e.stopPropagation()
                            setPushToTalkEnabled((prev) => !prev)
                        }}
                        title="Enable push-to-talk (hold V key to record)"
                    >
                        {pushToTalkEnabled ? (
                            <>
                                <Radio className="mr-1 h-3 w-3" /> PTT On
                            </>
                        ) : (
                            <>
                                <Radio className="mr-1 h-3 w-3" /> PTT Off
                            </>
                        )}
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 px-2 text-xs"
                        onClick={(event) => {
                            event.stopPropagation()
                            setChatOpen((prev) => !prev)
                        }}
                    >
                        Messages {chatOpen ? <ChevronUp className="ml-1 h-4 w-4" /> : <ChevronDown className="ml-1 h-4 w-4" />}
                    </Button>
                </div>
            </div>

            {statusMessage && (
                <div className="border-b border-destructive/30 bg-destructive/10 px-3 py-1 text-xs text-destructive">
                    {statusMessage}
                </div>
            )}
            
            {/* Status indicator for intro or PTT */}
            {(pushToTalkEnabled || isPlayingIntro) && (
                <div className={cn(
                    'border-b border-border px-3 py-1.5 text-xs',
                    pushToTalkActive ? 'bg-primary/10 text-primary' : 'bg-muted/30 text-muted-foreground'
                )}>
                    {isPlayingIntro && (
                        <span className="flex items-center gap-2">
                            <span className="inline-block h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                            Introducing the problem...
                        </span>
                    )}
                    {!isPlayingIntro && isRecording && (
                        <span className="flex items-center gap-2">
                            <span className="inline-block h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                            Recording... (hold V)
                        </span>
                    )}
                    {!isPlayingIntro && isProcessing && (
                        <span className="flex items-center gap-2">
                            <span className="inline-block h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
                            Processing...
                        </span>
                    )}
                    {!isPlayingIntro && isPlaying && (
                        <span className="flex items-center gap-2">
                            <span className="inline-block h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                            Playing response...
                        </span>
                    )}
                    {!pushToTalkActive && pushToTalkEnabled && (
                        <span className="italic">Press and hold V to speak</span>
                    )}
                </div>
            )}

            <div className="relative aspect-video w-full overflow-hidden bg-muted">
                <TalkingHead 
                    audioUrl={currentAudioUrl}
                    text={currentText}
                    onSpeakingStateChange={(speaking) => {
                        setAvatarSpeaking(speaking)
                        // If intro was playing and just finished speaking, mark as complete
                        if (!speaking && isPlayingIntro && currentAudioUrl) {
                            console.log('[FloatingPane] Intro lipsync complete, marking as finished')
                            // Wait a moment then clear
                            setTimeout(() => {
                                setCurrentAudioUrl(null)
                                setCurrentText(null)
                            }, 500)
                        }
                    }}
                />
            </div>
            
            {/* Live Transcript Section */}
            {pushToTalkEnabled && (
                <div className="border-t border-border">
                    <button
                        className="w-full px-3 py-2 text-left text-xs font-medium text-foreground hover:bg-muted/30 transition-colors flex items-center justify-between"
                        onClick={() => setTranscriptExpanded((prev) => !prev)}
                    >
                        <span>Live Transcript</span>
                        {transcriptExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                    {transcriptExpanded && (
                        <div className="px-3 pb-3">
                            <LiveTranscript apiBase={apiBase} />
                        </div>
                    )}
                </div>
            )}

            <div className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${chatOpen ? 'grid-rows-[1fr_auto]' : 'grid-rows-[0fr]'}`}>
                <div className="min-h-0 overflow-hidden">
                    <div ref={chatBodyRef} className="flex max-h-64 min-h-0 flex-col gap-3 overflow-y-auto px-3 py-3">
                        {messages.map(({ id, role, content }) => (
                            <div
                                key={id}
                                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${role === 'user' ? 'ml-auto bg-primary text-primary-foreground' : 'mr-auto bg-accent text-accent-foreground'}`}
                            >
                                {role === 'assistant' ? (
                                    <div
                                        className="space-y-1 leading-relaxed [&_strong]:font-semibold"
                                        dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
                                    />
                                ) : (
                                    content
                                )}
                            </div>
                        ))}
                    </div>
                </div>
                <form
                    onSubmit={handleSendMessage}
                    className={`border-t border-border bg-surface px-3 py-2 ${chatOpen ? 'visible opacity-100' : 'invisible opacity-0'} transition-opacity duration-200`}
                >
                    <div className="flex items-center gap-2">
                        <input
                            value={draft}
                            onChange={(event) => setDraft(event.target.value)}
                            placeholder="Type a message…"
                            className="flex-1 rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary/60"
                        />
                        <Button type="submit" size="sm" className="h-10 px-3" aria-label="Send message">
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                </form>
            </div>
            </div>
        </div>
    )
}
