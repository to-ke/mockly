import { useEffect, useRef, useState, useCallback } from 'react'
import { TalkingHead as TalkingHeadEngine } from '@met4citizen/talkinghead'
import { defaultTalkingHeadModelUrl } from '@/lib/talkingHeadPreload'
import { cn } from '@/lib/cn'

type TalkingHeadStatus = 'idle' | 'loading' | 'ready' | 'error' | 'speaking'

type WordTimestamp = {
  word: string
  start_time: number
  end_time: number
  confidence?: number
}

type CaptionData = {
  words: WordTimestamp[]
  status: 'active' | 'no_data' | 'error'
  last_updated: number
  word_count?: number
  source?: string
}

type TalkingHeadSyncProps = {
  modelUrl?: string
  className?: string
  audioUrl?: string | null
  enableSync?: boolean
  onSpeakingStateChange?: (speaking: boolean) => void
}

const REQUIRED_MORPH_TARGETS = ['eyeBlinkLeft', 'eyeBlinkRight', 'jawOpen', 'mouthSmileLeft', 'mouthSmileRight']
const DEFAULT_MODEL_URL = defaultTalkingHeadModelUrl
const AVATAR_BACKGROUND = '#0f172a'
const CAPTION_POLL_INTERVAL = 150 // Poll every 150ms for low latency

function validateMorphTargets(head: TalkingHeadEngine): string | null {
  const avatarMorphTargets = (head as unknown as { mtAvatar?: Record<string, unknown> }).mtAvatar ?? {}
  const missing = REQUIRED_MORPH_TARGETS.filter((name) => !(name in avatarMorphTargets))
  if (missing.length) {
    return `Avatar missing required blend shapes (${missing.join(', ')}). Re-export from Ready Player Me with "ARKit + Oculus Visemes" enabled.`
  }
  return null
}

export function TalkingHeadSync({
  modelUrl = DEFAULT_MODEL_URL,
  className,
  audioUrl,
  enableSync = true,
  onSpeakingStateChange,
}: TalkingHeadSyncProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const headRef = useRef<TalkingHeadEngine | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const pollIntervalRef = useRef<number | null>(null)
  const captionsRef = useRef<CaptionData | null>(null)

  const [status, setStatus] = useState<TalkingHeadStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [captions, setCaptions] = useState<CaptionData | null>(null)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [currentWord, setCurrentWord] = useState<string | null>(null)

  // Initialize TalkingHead avatar
  useEffect(() => {
    const container = containerRef.current
    if (!container || typeof window === 'undefined') return undefined

    let disposed = false
    setStatus('loading')
    setError(null)

    const init = async () => {
      try {
        headRef.current?.dispose()
        const head = new TalkingHeadEngine(container, {
          cameraView: 'head',
          cameraRotateEnable: false,
          cameraPanEnable: false,
          cameraZoomEnable: false,
          modelPixelRatio: window.devicePixelRatio ?? 1,
          lightAmbientIntensity: 0.8,
          lightDirectIntensity: 14,
          lightSpotIntensity: 4,
          dracoEnabled: true,
        })
        headRef.current = head

        await head.showAvatar({
          url: modelUrl,
          avatarMood: 'neutral',
          cameraView: 'head',
          lipsyncLang: 'en',
        })

        const morphError = validateMorphTargets(head)
        if (morphError) {
          throw new Error(morphError)
        }

        if (!disposed) {
          setStatus('ready')
          console.log('[TalkingHeadSync] Avatar ready')
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err)
        console.error('Failed to initialise TalkingHead', err)
        if (!disposed) {
          setError(message)
          setStatus('error')
        }
      }
    }

    init()

    return () => {
      disposed = true
      headRef.current?.dispose()
      headRef.current = null
    }
  }, [modelUrl])

  // Poll for live captions
  useEffect(() => {
    if (!enableSync || !audioUrl) {
      setCaptions(null)
      captionsRef.current = null
      return
    }

    const pollCaptions = async () => {
      try {
        const response = await fetch('/api/workflow/captions/live')
        if (response.ok) {
          const data: CaptionData = await response.json()
          setCaptions(data)
          captionsRef.current = data
          if (data.word_count && data.word_count > 0) {
            console.log(`[TalkingHeadSync] ✅ Fetched ${data.word_count} caption words from ${data.source || 'unknown'}`)
          }
        }
      } catch (err) {
        console.error('[TalkingHeadSync] Failed to fetch captions:', err)
      }
    }

    // Initial fetch
    pollCaptions()

    // Start polling
    pollIntervalRef.current = window.setInterval(pollCaptions, CAPTION_POLL_INTERVAL)

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  }, [enableSync, audioUrl])

  // Reset mouth to neutral position
  const resetMouth = useCallback(() => {
    const head = headRef.current
    if (!head) return

    try {
      const headAny = head as any
      if (headAny.avatar && headAny.avatar.morphTargetInfluences) {
        const influences = headAny.avatar.morphTargetInfluences
        const dictionary = headAny.avatar.morphTargetDictionary

        if (dictionary.jawOpen !== undefined) {
          influences[dictionary.jawOpen] = 0
        }
      }
    } catch (err) {
      console.warn('[TalkingHeadSync] Reset mouth error:', err)
    }
  }, [])

  // Animate mouth based on current word
  const animateMouth = useCallback((word: string, progress: number) => {
    const head = headRef.current
    if (!head) return

    try {
      const headAny = head as any
      if (!headAny.avatar || !headAny.avatar.morphTargetInfluences) return

      const influences = headAny.avatar.morphTargetInfluences
      const dictionary = headAny.avatar.morphTargetDictionary

      // Simple phoneme approximation
      const hasOpenVowel = /[aeiou]/i.test(word)
      const hasLabial = /[bpmw]/i.test(word)

      // Natural jaw movement with sine wave
      const jawAmount = hasOpenVowel ? 0.6 : 0.4
      const jawOpen = jawAmount * Math.sin(progress * Math.PI)

      if (dictionary.jawOpen !== undefined) {
        influences[dictionary.jawOpen] = Math.max(0, jawOpen)
      }

      // Add subtle smile for certain sounds
      if (hasLabial && dictionary.mouthSmileLeft !== undefined && dictionary.mouthSmileRight !== undefined) {
        const smileAmount = 0.1 * Math.sin(progress * Math.PI)
        influences[dictionary.mouthSmileLeft] = smileAmount
        influences[dictionary.mouthSmileRight] = smileAmount
      }
    } catch (err) {
      console.warn('[TalkingHeadSync] Animate mouth error:', err)
    }
  }, [])

  // Handle audio playback with synchronized lipsync
  const handleAudioPlay = useCallback(() => {
    const head = headRef.current
    const audio = audioRef.current

    if (!head || !audio) return
    
    // Wait for avatar to be fully loaded before starting animation
    if (status !== 'ready') {
      console.warn('[TalkingHeadSync] Avatar not ready yet, waiting...')
      return
    }

    setIsSpeaking(true)
    setStatus('speaking')
    onSpeakingStateChange?.(true)

    console.log('[TalkingHeadSync] Starting synchronized playback')
    console.log('[TalkingHeadSync] Head ready:', !!head, 'Audio ready:', !!audio)

    // Sync loop
    const syncLoop = () => {
      const headInstance = headRef.current
      const audioInstance = audioRef.current

      if (!audioInstance || audioInstance.paused || audioInstance.ended) {
        setIsSpeaking(false)
        setStatus('ready')
        setCurrentWord(null)
        onSpeakingStateChange?.(false)
        resetMouth()

        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
          animationFrameRef.current = null
        }
        return
      }

      const currentTime = audioInstance.currentTime

      // Read the latest captions from ref (might update during playback)
      const captionData = captionsRef.current

      // Find current word being spoken
      if (captionData?.words && captionData.words.length > 0) {
        const word = captionData.words.find(
          w => currentTime >= w.start_time && currentTime <= w.end_time
        )

        if (word) {
          setCurrentWord(word.word)

          // Calculate progress through the word (0 to 1)
          const progress = (currentTime - word.start_time) / (word.end_time - word.start_time)
          animateMouth(word.word, progress)
        } else {
          setCurrentWord(null)
          // Smoothly close mouth between words
          if (headInstance) {
            const headAny = headInstance as any
            if (headAny.avatar && headAny.avatar.morphTargetInfluences) {
              const influences = headAny.avatar.morphTargetInfluences
              const dictionary = headAny.avatar.morphTargetDictionary

              if (dictionary.jawOpen !== undefined) {
                influences[dictionary.jawOpen] *= 0.85 // Exponential decay
              }
            }
          }
        }
      } else {
        // No captions available - use simple audio-based animation
        // This provides basic mouth movement even without word timing
        const simpleJaw = 0.3 + Math.sin(currentTime * 8) * 0.2

        try {
          if (headInstance) {
            const headAny = headInstance as any
            if (headAny.avatar && headAny.avatar.morphTargetInfluences) {
              const influences = headAny.avatar.morphTargetInfluences
              const dictionary = headAny.avatar.morphTargetDictionary

              if (dictionary.jawOpen !== undefined) {
                influences[dictionary.jawOpen] = simpleJaw

                // Log occasionally to confirm animation is running
                if (Math.floor(currentTime * 10) % 10 === 0) {
                  console.log(`[TalkingHeadSync] Fallback animation: time=${currentTime.toFixed(2)}s, jaw=${simpleJaw.toFixed(3)}`)
                }
              } else {
                console.warn('[TalkingHeadSync] jawOpen morph target not found')
              }
            } else {
              console.warn('[TalkingHeadSync] Avatar or morphTargetInfluences not available')
            }
          }
        } catch (err) {
          console.warn('[TalkingHeadSync] Fallback animation error:', err)
        }
      }

      animationFrameRef.current = requestAnimationFrame(syncLoop)
    }

    syncLoop()
  }, [status, onSpeakingStateChange, resetMouth, animateMouth])

  const handleAudioEnded = useCallback(() => {
    console.log('[TalkingHeadSync] Audio playback ended')
    setIsSpeaking(false)
    setStatus('ready')
    setCurrentWord(null)
    onSpeakingStateChange?.(false)

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    resetMouth()
  }, [onSpeakingStateChange, resetMouth])

  // Manage audio element
  useEffect(() => {
    console.log('[TalkingHeadSync] audioUrl changed:', audioUrl ? 'URL provided' : 'null')

    if (!audioUrl) {
      // Clean up audio
      if (audioRef.current) {
        console.log('[TalkingHeadSync] Cleaning up previous audio')
        audioRef.current.pause()
        audioRef.current.src = ''
        audioRef.current = null
      }
      setIsSpeaking(false)
      setCurrentWord(null)
      resetMouth()
      return
    }

    console.log('[TalkingHeadSync] Creating new audio element for:', audioUrl.substring(0, 50))

    // Create and configure audio element
    const audio = new Audio(audioUrl)
    audio.crossOrigin = 'anonymous'
    audio.preload = 'auto'
    audioRef.current = audio

    audio.addEventListener('play', handleAudioPlay)
    audio.addEventListener('ended', handleAudioEnded)
    audio.addEventListener('pause', handleAudioEnded)
    audio.addEventListener('error', (e) => {
      console.error('[TalkingHeadSync] Audio error:', e)
      setError('Failed to play audio')
    })

    // Start playback
    console.log('[TalkingHeadSync] Starting audio playback...')
    audio.play().catch(err => {
      console.error('[TalkingHeadSync] Audio playback failed:', err)
      setError('Failed to play audio')
    })

    return () => {
      audio.pause()
      audio.removeEventListener('play', handleAudioPlay)
      audio.removeEventListener('ended', handleAudioEnded)
      audio.removeEventListener('pause', handleAudioEnded)

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
        animationFrameRef.current = null
      }
    }
  }, [audioUrl, handleAudioPlay, handleAudioEnded, resetMouth])

  const overlayMessage = (() => {
    if (status === 'error' && error) return error
    if (status === 'loading' || status === 'idle') return 'Loading avatar…'
    return null
  })()

  return (
    <div className={cn('relative h-full w-full', className)}>
      <div
        ref={containerRef}
        className="h-full w-full overflow-hidden rounded-2xl"
        style={{ backgroundColor: AVATAR_BACKGROUND }}
      />
      {overlayMessage && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center rounded-2xl bg-surface/70 text-sm text-muted-foreground backdrop-blur-sm">
          {overlayMessage}
        </div>
      )}
      {isSpeaking && currentWord && (
        <div className="pointer-events-none absolute bottom-4 left-0 right-0 px-4">
          <div className="rounded-lg bg-black/70 px-4 py-2 text-center text-sm text-white/90 backdrop-blur-sm">
            <span className="font-medium">{currentWord}</span>
          </div>
        </div>
      )}
    </div>
  )
}

