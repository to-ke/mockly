/**
 * Audio optimization utilities for low-latency playback
 * and efficient streaming
 */

export class AudioStreamOptimizer {
  private static audioContext: AudioContext | null = null

  /**
   * Pre-warm audio context to avoid initialization delay
   * Call this early in your app lifecycle (e.g., on user interaction)
   */
  static warmupAudioContext(): AudioContext {
    if (this.audioContext) {
      return this.audioContext
    }

    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    
    // Play silent audio to unlock iOS audio
    // This is required on iOS Safari due to autoplay restrictions
    const buffer = ctx.createBuffer(1, 1, 22050)
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.start(0)
    
    this.audioContext = ctx
    console.log('[AudioOptimizer] Audio context warmed up')
    
    return ctx
  }

  /**
   * Get the shared audio context instance
   */
  static getAudioContext(): AudioContext | null {
    return this.audioContext
  }

  /**
   * Use Web Audio API for lower latency playback
   * Returns the audio source node for further manipulation
   */
  static async playAudioWithLowLatency(
    audioBlob: Blob,
    context?: AudioContext
  ): Promise<AudioBufferSourceNode> {
    const ctx = context || this.warmupAudioContext()
    
    const arrayBuffer = await audioBlob.arrayBuffer()
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer)
    
    const source = ctx.createBufferSource()
    source.buffer = audioBuffer
    source.connect(ctx.destination)
    source.start(0)
    
    console.log('[AudioOptimizer] Low-latency playback started')
    
    return source
  }

  /**
   * Prefetch and cache audio data for instant playback
   */
  static async prefetchAudio(url: string): Promise<Blob> {
    console.log('[AudioOptimizer] Prefetching audio:', url)
    const response = await fetch(url, {
      mode: 'cors',
      cache: 'force-cache',
    })
    
    if (!response.ok) {
      throw new Error(`Failed to prefetch audio: ${response.statusText}`)
    }
    
    return await response.blob()
  }

  /**
   * Create audio element optimized for low latency streaming
   */
  static createLowLatencyAudioElement(): HTMLAudioElement {
    const audio = new Audio()
    
    // Minimize buffering for lower latency
    audio.preload = 'auto'
    
    // Set crossOrigin for CORS support
    audio.crossOrigin = 'anonymous'
    
    // Optimize for low latency (browser-specific features)
    if ('mozAudioChannelType' in audio) {
      // Firefox-specific
      (audio as any).mozAudioChannelType = 'content'
    }
    
    console.log('[AudioOptimizer] Low-latency audio element created')
    
    return audio
  }

  /**
   * Measure audio latency by playing a click and measuring timing
   * Useful for debugging audio sync issues
   */
  static async measureAudioLatency(): Promise<number> {
    const ctx = this.warmupAudioContext()
    
    const startTime = performance.now()
    
    // Create a short click sound
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 0.01, ctx.sampleRate)
    const data = buffer.getChannelData(0)
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random() * 0.1
    }
    
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    
    return new Promise((resolve) => {
      source.onended = () => {
        const latency = performance.now() - startTime
        console.log('[AudioOptimizer] Measured latency:', latency, 'ms')
        resolve(latency)
      }
      source.start(0)
    })
  }

  /**
   * Dispose of the audio context to free resources
   */
  static dispose(): void {
    if (this.audioContext) {
      this.audioContext.close().catch(() => {
        // Ignore close errors
      })
      this.audioContext = null
      console.log('[AudioOptimizer] Audio context disposed')
    }
  }
}

/**
 * Debounced polling utility to avoid excessive requests
 * Useful for polling caption data without overwhelming the server
 */
export function createDebouncedPoller(
  fetchFn: () => Promise<void>,
  interval: number
): {
  start: () => void
  stop: () => void
  isRunning: () => boolean
} {
  let timeoutId: number | null = null
  let isRunning = false
  let isActive = false

  const poll = async () => {
    if (isRunning || !isActive) return
    
    isRunning = true
    try {
      await fetchFn()
    } catch (err) {
      console.error('[DebouncedPoller] Fetch error:', err)
    } finally {
      isRunning = false
    }
    
    if (isActive) {
      timeoutId = window.setTimeout(poll, interval)
    }
  }

  return {
    start: () => {
      if (isActive) return
      
      isActive = true
      console.log('[DebouncedPoller] Started with interval:', interval, 'ms')
      poll()
    },
    
    stop: () => {
      isActive = false
      
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = null
      }
      
      console.log('[DebouncedPoller] Stopped')
    },
    
    isRunning: () => isActive,
  }
}

/**
 * Caption cache to reduce redundant network requests
 * Caches caption data with TTL (time-to-live)
 */
export class CaptionCache {
  private cache: Map<string, {
    data: any
    timestamp: number
  }> = new Map()
  
  private maxAge: number

  constructor(maxAgeMs: number = 5000) {
    this.maxAge = maxAgeMs
  }

  /**
   * Get cached data if available and not expired
   */
  get(key: string): any | null {
    const entry = this.cache.get(key)
    if (!entry) return null
    
    if (Date.now() - entry.timestamp > this.maxAge) {
      this.cache.delete(key)
      return null
    }
    
    return entry.data
  }

  /**
   * Store data in cache with current timestamp
   */
  set(key: string, data: any): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    })
  }

  /**
   * Check if key exists and is not expired
   */
  has(key: string): boolean {
    return this.get(key) !== null
  }

  /**
   * Clear all cached data
   */
  clear(): void {
    this.cache.clear()
  }

  /**
   * Remove expired entries
   */
  cleanup(): void {
    const now = Date.now()
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.maxAge) {
        this.cache.delete(key)
      }
    }
  }

  /**
   * Get cache statistics
   */
  getStats(): {
    size: number
    keys: string[]
  } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    }
  }
}

/**
 * Request animation frame throttle utility
 * Ensures callback is called at most once per frame
 */
export function createRAFThrottle(callback: () => void): () => void {
  let rafId: number | null = null
  let latestArgs: any[] = []

  return function throttled(...args: any[]) {
    latestArgs = args
    
    if (rafId !== null) return
    
    rafId = requestAnimationFrame(() => {
      callback.apply(null, latestArgs)
      rafId = null
    })
  }
}

/**
 * Simple performance monitor for debugging
 */
export class PerformanceMonitor {
  private metrics: Map<string, number[]> = new Map()
  private maxSamples = 100

  /**
   * Record a timing measurement
   */
  record(name: string, value: number): void {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, [])
    }
    
    const samples = this.metrics.get(name)!
    samples.push(value)
    
    // Keep only recent samples
    if (samples.length > this.maxSamples) {
      samples.shift()
    }
  }

  /**
   * Get statistics for a metric
   */
  getStats(name: string): {
    avg: number
    min: number
    max: number
    last: number
    count: number
  } | null {
    const samples = this.metrics.get(name)
    if (!samples || samples.length === 0) return null
    
    const sum = samples.reduce((a, b) => a + b, 0)
    const avg = sum / samples.length
    const min = Math.min(...samples)
    const max = Math.max(...samples)
    const last = samples[samples.length - 1]
    
    return { avg, min, max, last, count: samples.length }
  }

  /**
   * Log all metrics to console
   */
  logAll(): void {
    console.group('[PerformanceMonitor] Metrics')
    for (const [name, samples] of this.metrics.entries()) {
      const stats = this.getStats(name)
      if (stats) {
        console.log(
          `${name}:`,
          `avg=${stats.avg.toFixed(2)}ms`,
          `min=${stats.min.toFixed(2)}ms`,
          `max=${stats.max.toFixed(2)}ms`,
          `last=${stats.last.toFixed(2)}ms`,
          `(n=${stats.count})`
        )
      }
    }
    console.groupEnd()
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics.clear()
  }
}

