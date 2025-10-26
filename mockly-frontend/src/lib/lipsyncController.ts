import { TalkingHead } from '@met4citizen/talkinghead'

export interface WordTimestamp {
  word: string
  start_time: number
  end_time: number
  confidence?: number
}

/**
 * Advanced lipsync controller for TalkingHead avatar
 * Provides multiple synchronization methods for different use cases
 */
export class LipsyncController {
  private head: TalkingHead
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private dataArray: Uint8Array | null = null
  private animationId: number | null = null
  private isRunning = false

  constructor(head: TalkingHead) {
    this.head = head
  }

  /**
   * Method 1: Use TalkingHead's built-in speakAudio with text
   * This is the EASIEST and most reliable method for pre-recorded audio
   */
  async speakWithText(audioBlob: Blob, text: string): Promise<void> {
    try {
      // Convert blob to base64 data URL
      const arrayBuffer = await audioBlob.arrayBuffer()
      const base64 = btoa(
        new Uint8Array(arrayBuffer).reduce(
          (data, byte) => data + String.fromCharCode(byte),
          ''
        )
      )
      const dataUrl = `data:audio/mpeg;base64,${base64}`

      // Use TalkingHead's built-in method
      // It automatically handles lipsync based on the text
      await (this.head as any).speakAudio(dataUrl, text, {
        lipsyncLang: 'en',
      })
      
      console.log('[LipsyncController] speakWithText completed')
    } catch (err) {
      console.error('[LipsyncController] speakWithText failed:', err)
      throw err
    }
  }

  /**
   * Method 2: Audio amplitude-based lipsync
   * Use this for real-time streaming audio without word timestamps
   */
  async startAudioBasedLipsync(audioElement: HTMLAudioElement): Promise<void> {
    if (this.isRunning) {
      console.warn('[LipsyncController] Already running, stopping previous instance')
      this.stop()
    }

    try {
      // Create audio context for analysis
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      this.analyser = this.audioContext.createAnalyser()
      this.analyser.fftSize = 256
      this.analyser.smoothingTimeConstant = 0.8
      
      const bufferLength = this.analyser.frequencyBinCount
      this.dataArray = new Uint8Array(bufferLength)

      // Connect audio element to analyser
      const source = this.audioContext.createMediaElementSource(audioElement)
      source.connect(this.analyser)
      this.analyser.connect(this.audioContext.destination)

      this.isRunning = true

      // Start animation loop
      this.animateFromAudio()
      
      console.log('[LipsyncController] Audio-based lipsync started')
    } catch (err) {
      console.error('[LipsyncController] Audio-based lipsync failed:', err)
      this.isRunning = false
    }
  }

  /**
   * Animate mouth based on audio amplitude
   */
  private animateFromAudio(): void {
    if (!this.isRunning || !this.analyser || !this.dataArray) return

    // Get frequency data
    this.analyser.getByteFrequencyData(this.dataArray)

    // Calculate average amplitude across frequency bins
    const average = this.dataArray.reduce((a, b) => a + b, 0) / this.dataArray.length
    
    // Normalize to 0-1 range
    const normalizedAmplitude = Math.min(average / 128, 1)

    // Apply exponential scaling for more natural movement
    const scaledAmplitude = Math.pow(normalizedAmplitude, 1.5)

    // Apply to jaw morph target
    try {
      const headAny = this.head as any
      if (headAny.avatar && headAny.avatar.morphTargetInfluences) {
        const influences = headAny.avatar.morphTargetInfluences
        const dictionary = headAny.avatar.morphTargetDictionary

        // Jaw open based on amplitude
        if (dictionary.jawOpen !== undefined) {
          influences[dictionary.jawOpen] = scaledAmplitude * 0.7
        }

        // Add subtle mouth movements for realism
        if (normalizedAmplitude > 0.1) {
          if (dictionary.mouthSmileLeft !== undefined) {
            influences[dictionary.mouthSmileLeft] = scaledAmplitude * 0.15
          }
          if (dictionary.mouthSmileRight !== undefined) {
            influences[dictionary.mouthSmileRight] = scaledAmplitude * 0.15
          }
        }
      }
    } catch (err) {
      console.warn('[LipsyncController] Morph target update failed:', err)
    }

    // Continue animation
    this.animationId = requestAnimationFrame(() => this.animateFromAudio())
  }

  /**
   * Method 3: Word-timestamp based lipsync (most precise)
   * Use this when you have word-level timestamps from transcription
   */
  startWordBasedLipsync(
    audioElement: HTMLAudioElement,
    words: WordTimestamp[]
  ): void {
    if (this.isRunning) {
      console.warn('[LipsyncController] Already running, stopping previous instance')
      this.stop()
    }

    this.isRunning = true
    
    console.log(`[LipsyncController] Word-based lipsync started with ${words.length} words`)

    const syncLoop = () => {
      if (!this.isRunning || audioElement.paused || audioElement.ended) {
        this.stop()
        return
      }

      const currentTime = audioElement.currentTime

      // Find current word
      const currentWord = words.find(
        w => currentTime >= w.start_time && currentTime <= w.end_time
      )

      if (currentWord) {
        const progress = 
          (currentTime - currentWord.start_time) / 
          (currentWord.end_time - currentWord.start_time)

        // Use phoneme-based animation
        this.animatePhoneme(currentWord.word, progress)
      } else {
        // Smoothly close mouth between words
        this.smoothCloseMouth()
      }

      this.animationId = requestAnimationFrame(syncLoop)
    }

    syncLoop()
  }

  /**
   * Animate based on phoneme characteristics of the word
   */
  private animatePhoneme(word: string, progress: number): void {
    try {
      const headAny = this.head as any
      if (!headAny.avatar || !headAny.avatar.morphTargetInfluences) return

      const influences = headAny.avatar.morphTargetInfluences
      const dictionary = headAny.avatar.morphTargetDictionary

      // Simple phoneme approximation based on word characteristics
      const hasOpenVowel = /[aeiou]/i.test(word)
      const hasLabial = /[bpmw]/i.test(word)
      const hasDental = /[td]/i.test(word)
      
      // Jaw movement (sine wave for natural open-close motion)
      const jawAmount = hasOpenVowel ? 0.6 : 0.35
      const jawOpen = jawAmount * Math.sin(progress * Math.PI)

      if (dictionary.jawOpen !== undefined) {
        influences[dictionary.jawOpen] = Math.max(0, jawOpen)
      }

      // Lip compression for labial sounds (b, p, m, w)
      if (hasLabial) {
        const lipCompression = 0.2 * Math.sin(progress * Math.PI * 2)
        
        if (dictionary.mouthPucker !== undefined) {
          influences[dictionary.mouthPucker] = Math.max(0, lipCompression)
        }
      }

      // Slight smile variation for natural movement
      const smileVariation = 0.1 * Math.sin(progress * Math.PI)
      
      if (dictionary.mouthSmileLeft !== undefined) {
        influences[dictionary.mouthSmileLeft] = Math.max(0, smileVariation)
      }
      if (dictionary.mouthSmileRight !== undefined) {
        influences[dictionary.mouthSmileRight] = Math.max(0, smileVariation)
      }
    } catch (err) {
      console.warn('[LipsyncController] Phoneme animation failed:', err)
    }
  }

  /**
   * Smoothly close mouth with exponential decay
   */
  private smoothCloseMouth(): void {
    try {
      const headAny = this.head as any
      if (!headAny.avatar || !headAny.avatar.morphTargetInfluences) return

      const influences = headAny.avatar.morphTargetInfluences
      const dictionary = headAny.avatar.morphTargetDictionary

      // Exponential decay for smooth closing
      const decayFactor = 0.88

      if (dictionary.jawOpen !== undefined) {
        influences[dictionary.jawOpen] *= decayFactor
      }

      if (dictionary.mouthSmileLeft !== undefined) {
        influences[dictionary.mouthSmileLeft] *= decayFactor
      }

      if (dictionary.mouthSmileRight !== undefined) {
        influences[dictionary.mouthSmileRight] *= decayFactor
      }

      if (dictionary.mouthPucker !== undefined) {
        influences[dictionary.mouthPucker] *= decayFactor
      }
    } catch (err) {
      console.warn('[LipsyncController] Smooth close failed:', err)
    }
  }

  /**
   * Reset mouth to neutral position immediately
   */
  resetMouth(): void {
    try {
      const headAny = this.head as any
      if (!headAny.avatar || !headAny.avatar.morphTargetInfluences) return

      const influences = headAny.avatar.morphTargetInfluences
      const dictionary = headAny.avatar.morphTargetDictionary

      if (dictionary.jawOpen !== undefined) {
        influences[dictionary.jawOpen] = 0
      }

      if (dictionary.mouthSmileLeft !== undefined) {
        influences[dictionary.mouthSmileLeft] = 0
      }

      if (dictionary.mouthSmileRight !== undefined) {
        influences[dictionary.mouthSmileRight] = 0
      }

      if (dictionary.mouthPucker !== undefined) {
        influences[dictionary.mouthPucker] = 0
      }
    } catch (err) {
      console.warn('[LipsyncController] Reset failed:', err)
    }
  }

  /**
   * Stop all lipsync animation
   */
  stop(): void {
    this.isRunning = false

    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }

    if (this.audioContext) {
      this.audioContext.close().catch(() => {
        // Ignore close errors
      })
      this.audioContext = null
    }

    this.analyser = null
    this.dataArray = null

    this.resetMouth()
    
    console.log('[LipsyncController] Stopped')
  }

  /**
   * Check if lipsync is currently running
   */
  get running(): boolean {
    return this.isRunning
  }
}

