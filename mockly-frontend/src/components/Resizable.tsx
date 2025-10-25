import { useCallback, useEffect, useRef, useState } from 'react'


export function HorizontalResizable({ left, right }: { left: React.ReactNode; right: React.ReactNode }) {
    const containerRef = useRef<HTMLDivElement | null>(null)
    const dragStateRef = useRef<{ startX: number; startWidth: number }>({ startX: 0, startWidth: 600 })
    const isDraggingRef = useRef(false)
    const [dragging, setDragging] = useState(false)
    const [leftWidth, setLeftWidth] = useState(600)


    const clampWidth = useCallback(
        (desired: number) => {
            const container = containerRef.current
            const containerWidth = container?.getBoundingClientRect().width ?? desired
            const minLeft = 240
            const minRight = 240
            const maxAllowed = Math.max(containerWidth - minRight, minLeft)
            return Math.min(Math.max(desired, minLeft), maxAllowed)
        },
        []
    )


    const syncWidth = useCallback(() => {
        setLeftWidth((prev) => clampWidth(prev))
    }, [clampWidth])


    useEffect(() => {
        syncWidth()
        window.addEventListener('resize', syncWidth)
        let observer: ResizeObserver | undefined
        if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
            observer = new ResizeObserver(syncWidth)
            observer.observe(containerRef.current)
        }
        return () => {
            window.removeEventListener('resize', syncWidth)
            observer?.disconnect()
        }
    }, [syncWidth])


    const handlePointerMove = useCallback(
        (event: PointerEvent) => {
            if (!isDraggingRef.current) return
            event.preventDefault()
            const delta = event.clientX - dragStateRef.current.startX
            const nextWidth = clampWidth(dragStateRef.current.startWidth + delta)
            setLeftWidth(nextWidth)
        },
        [clampWidth]
    )


    const stopDragging = useCallback(() => {
        if (!isDraggingRef.current) return
        isDraggingRef.current = false
        setDragging(false)
        document.body.style.userSelect = ''
        window.removeEventListener('pointermove', handlePointerMove)
        window.removeEventListener('pointerup', stopDragging)
    }, [handlePointerMove])


    useEffect(() => {
        return () => {
            stopDragging()
        }
    }, [stopDragging])


    const handlePointerDown = useCallback(
        (event: React.PointerEvent<HTMLDivElement>) => {
            if (!containerRef.current) return
            event.preventDefault()
            isDraggingRef.current = true
            setDragging(true)
            dragStateRef.current = {
                startX: event.clientX,
                startWidth: leftWidth,
            }
            document.body.style.userSelect = 'none'
            window.addEventListener('pointermove', handlePointerMove)
            window.addEventListener('pointerup', stopDragging)
        },
        [handlePointerMove, leftWidth, stopDragging]
    )


    return (
        <div ref={containerRef} className="flex h-full min-h-0 min-w-0">
            <div className="flex min-h-0 min-w-0 pr-2" style={{ width: leftWidth }}>
                <div className="h-full min-h-0 min-w-0 flex-1">{left}</div>
            </div>
            <div
                role="separator"
                aria-orientation="vertical"
                aria-label="Resize editor"
                className={`resizer-handle${dragging ? ' resizer-handle-active' : ''}`}
                onPointerDown={handlePointerDown}
            />
            <div className="flex-1 min-h-0 min-w-0 pl-2">{right}</div>
        </div>
    )
}
