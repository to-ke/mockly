import { useEffect, useRef, useState } from 'react'
import { TalkingHead as TalkingHeadEngine } from '@met4citizen/talkinghead'
import { defaultTalkingHeadModelUrl } from '@/lib/talkingHeadPreload'
import { cn } from '@/lib/cn'

type TalkingHeadStatus = 'idle' | 'loading' | 'ready' | 'error'

type TalkingHeadProps = {
  modelUrl?: string
  className?: string
}

const REQUIRED_MORPH_TARGETS = ['eyeBlinkLeft', 'eyeBlinkRight', 'jawOpen', 'mouthSmileLeft', 'mouthSmileRight']
const DEFAULT_MODEL_URL = defaultTalkingHeadModelUrl
const AVATAR_BACKGROUND = '#0f172a'

function validateMorphTargets(head: TalkingHeadEngine): string | null {
  const avatarMorphTargets = (head as unknown as { mtAvatar?: Record<string, unknown> }).mtAvatar ?? {}
  const missing = REQUIRED_MORPH_TARGETS.filter((name) => !(name in avatarMorphTargets))
  if (missing.length) {
    return `Avatar missing required blend shapes (${missing.join(', ')}). Re-export from Ready Player Me with “ARKit + Oculus Visemes” enabled.`
  }
  return null
}

export function TalkingHead({ modelUrl = DEFAULT_MODEL_URL, className }: TalkingHeadProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const headRef = useRef<TalkingHeadEngine | null>(null)
  const [status, setStatus] = useState<TalkingHeadStatus>('idle')
  const [error, setError] = useState<string | null>(null)

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
        })

        const morphError = validateMorphTargets(head)
        if (morphError) {
          throw new Error(morphError)
        }

        if (!disposed) {
          setStatus('ready')
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
    </div>
  )
}
