# TalkingHead Lipsync Integration Guide

This guide explains how to use the live audio transcription and avatar lipsync features in your Mockly application.

## Overview

The system synchronizes audio playback with TalkingHead avatar lip movements using live caption data from the backend. It provides near-real-time lip sync for a natural conversation experience.

## Architecture

```
Backend (Python/FastAPI)
  ├── TTS Audio Generation (Deepgram)
  ├── LiveTTSCapture (writes captions to NDJSON)
  └── /api/workflow/captions/live endpoint
           ↓
Frontend (React/TypeScript)
  ├── TalkingHeadSync component
  ├── LipsyncController utility
  └── Audio playback with sync loop
```

## Quick Start

### 1. Backend Setup

The backend is already configured! Captions are automatically generated when TTS audio is created.

**Configuration** (in `.env`):
```bash
# Enable live caption generation (default: enabled)
TTS_LIVE_JSON_PATH=live_tts_captions.ndjson

# Deepgram settings
DEEPGRAM_API_KEY=your_key_here
DEEPGRAM_TTS_VOICE=aura-2-thalia-en
DEEPGRAM_SAMPLE_RATE=48000
```

### 2. Frontend Usage

#### Option A: Use the TalkingHeadSync Component (Recommended)

Replace your existing `TalkingHead` component with `TalkingHeadSync`:

```tsx
import { TalkingHeadSync } from '@/components/TalkingHeadSync'
import { useVoice } from '@/stores/voice'

function MyApp() {
  const { audioUrl, setAvatarSpeaking } = useVoice()

  return (
    <TalkingHeadSync
      audioUrl={audioUrl}
      enableSync={true}
      onSpeakingStateChange={setAvatarSpeaking}
      className="h-96"
    />
  )
}
```

**That's it!** The component handles everything:
- ✅ Fetches live captions from backend
- ✅ Synchronizes mouth movements with audio
- ✅ Shows current word being spoken
- ✅ Automatically cleans up on unmount

#### Option B: Use the LipsyncController Directly

For more control, use the `LipsyncController` class:

```tsx
import { LipsyncController } from '@/lib/lipsyncController'
import { Api } from '@/services/api'

// 1. Get your TalkingHead instance
const head = headRef.current

// 2. Create controller
const controller = new LipsyncController(head)

// 3. Fetch captions and start sync
const captions = await Api.fetchCaptions()
const audioElement = new Audio(audioUrl)

if (captions.words.length > 0) {
  controller.startWordBasedLipsync(audioElement, captions.words)
} else {
  // Fallback to audio-based sync
  controller.startAudioBasedLipsync(audioElement)
}

audioElement.play()

// 4. Clean up when done
controller.stop()
```

## API Reference

### TalkingHeadSync Component

```typescript
interface TalkingHeadSyncProps {
  modelUrl?: string              // Avatar model URL (default: Ready Player Me)
  className?: string             // CSS classes
  audioUrl?: string | null       // Audio to play and sync
  enableSync?: boolean           // Enable caption sync (default: true)
  onSpeakingStateChange?: (speaking: boolean) => void
}
```

### LipsyncController

```typescript
class LipsyncController {
  // Method 1: Use TalkingHead's built-in lipsync (best for pre-recorded)
  async speakWithText(audioBlob: Blob, text: string): Promise<void>

  // Method 2: Audio amplitude-based (for streaming without captions)
  async startAudioBasedLipsync(audioElement: HTMLAudioElement): Promise<void>

  // Method 3: Word-timestamp based (most precise)
  startWordBasedLipsync(
    audioElement: HTMLAudioElement,
    words: WordTimestamp[]
  ): void

  // Stop all animations
  stop(): void
}
```

### Caption Data Types

```typescript
interface WordTimestamp {
  word: string
  start_time: number      // seconds
  end_time: number        // seconds
  confidence?: number
}

interface CaptionDataResponse {
  words: WordTimestamp[]
  status: 'active' | 'no_data' | 'error'
  last_updated: number
  word_count?: number
}
```

### API Methods

```typescript
// Fetch live captions from backend
const captions = await Api.fetchCaptions()
```

## Performance Optimization

### 1. Pre-warm Audio Context

Call this early in your app (e.g., on user interaction):

```typescript
import { AudioStreamOptimizer } from '@/lib/audioOptimizations'

// On app mount or user interaction
AudioStreamOptimizer.warmupAudioContext()
```

### 2. Reduce Polling Latency

The `TalkingHeadSync` component polls every 150ms by default. Adjust if needed:

```typescript
// In TalkingHeadSync.tsx
const CAPTION_POLL_INTERVAL = 100 // 100ms for ultra-low latency
```

### 3. Use Performance Monitoring

```typescript
import { PerformanceMonitor } from '@/lib/audioOptimizations'

const monitor = new PerformanceMonitor()

// Record timing
const start = performance.now()
await fetchCaptions()
monitor.record('caption-fetch', performance.now() - start)

// Log stats
monitor.logAll()
```

## Troubleshooting

### Audio plays but no lip movement

**Check:**
1. Is `TTS_LIVE_JSON_PATH` set in backend `.env`?
2. Does `/api/workflow/captions/live` return data?
3. Is avatar model exported with ARKit visemes?

**Solution:**
```bash
# Backend: Verify captions are being generated
curl http://localhost:8000/api/workflow/captions/live

# Should return: {"words": [...], "status": "active"}
```

### Lip sync lags behind audio

**Solutions:**
1. Reduce polling interval to 100ms
2. Use Web Audio API instead of HTMLAudioElement
3. Check network latency to backend

### Choppy animations

**Solutions:**
1. Ensure you're using `requestAnimationFrame`
2. Reduce concurrent animations
3. Check avatar model complexity

### No captions available

**Check:**
1. Backend TTS has been called at least once
2. Caption file path is writable
3. No errors in backend logs

**Debug:**
```typescript
const captions = await Api.fetchCaptions()
console.log('Caption status:', captions.status)
console.log('Word count:', captions.word_count)
```

## Advanced Usage

### Custom Phoneme Mapping

Extend the `LipsyncController` for better accuracy:

```typescript
class CustomLipsyncController extends LipsyncController {
  private phonemeMap = {
    'a': { jawOpen: 0.8, mouthSmile: 0.1 },
    'ee': { jawOpen: 0.3, mouthSmile: 0.6 },
    'oo': { jawOpen: 0.5, mouthPucker: 0.7 },
    // Add more phonemes...
  }

  protected animatePhoneme(word: string, progress: number): void {
    // Your custom phoneme logic here
  }
}
```

### Adding Head Gestures

Enhance realism by adding subtle head movements:

```typescript
// In your sync loop
const time = performance.now() / 1000
const headRotationY = Math.sin(time * 0.5) * 0.05
const headRotationX = Math.sin(time * 0.3) * 0.03

if (headAny.avatar) {
  headAny.avatar.rotation.y = headRotationY
  headAny.avatar.rotation.x = headRotationX
}
```

### Eye Blinking

Add natural eye blinks during speech:

```typescript
setInterval(() => {
  if (isSpeaking && Math.random() > 0.7) {
    // Trigger blink
    if (dictionary.eyeBlinkLeft !== undefined) {
      influences[dictionary.eyeBlinkLeft] = 1
      influences[dictionary.eyeBlinkRight] = 1
      
      setTimeout(() => {
        influences[dictionary.eyeBlinkLeft] = 0
        influences[dictionary.eyeBlinkRight] = 0
      }, 150)
    }
  }
}, 3000) // Every 3 seconds
```

## Best Practices

1. **Always clean up**: Call `controller.stop()` when unmounting
2. **Handle errors gracefully**: Provide fallback to audio-based sync
3. **Monitor performance**: Use `PerformanceMonitor` to track latency
4. **Pre-load audio**: Use `AudioStreamOptimizer.prefetchAudio()`
5. **Test on mobile**: iOS has strict autoplay policies

## Examples

### Complete Integration Example

```tsx
import { useState, useEffect } from 'react'
import { TalkingHeadSync } from '@/components/TalkingHeadSync'
import { AudioStreamOptimizer } from '@/lib/audioOptimizations'
import { useVoice } from '@/stores/voice'

function InterviewScreen() {
  const { audioUrl, avatarSpeaking, setAvatarSpeaking } = useVoice()
  
  // Pre-warm audio context on mount
  useEffect(() => {
    AudioStreamOptimizer.warmupAudioContext()
  }, [])

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Avatar with lipsync */}
      <div className="col-span-1">
        <TalkingHeadSync
          audioUrl={audioUrl}
          enableSync={true}
          onSpeakingStateChange={setAvatarSpeaking}
          className="h-96"
        />
        
        {avatarSpeaking && (
          <div className="mt-2 text-center">
            <span className="text-sm text-muted">Speaking...</span>
          </div>
        )}
      </div>

      {/* Your other UI */}
      <div className="col-span-1">
        {/* Code editor, questions, etc. */}
      </div>
    </div>
  )
}
```

## Support

For issues or questions:
1. Check the backend logs for caption generation errors
2. Verify captions endpoint returns data
3. Test with audio-based sync as fallback
4. Review browser console for errors

## Related Documentation

- [TalkingHead Library Docs](https://github.com/met4citizen/TalkingHead)
- [Deepgram TTS API](https://developers.deepgram.com/docs/tts-introduction)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

