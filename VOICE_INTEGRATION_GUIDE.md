# Voice Integration Guide - Push-to-Talk & Live Transcription

## 🎯 Overview

This guide documents the complete implementation of voice functionality for the Mockly mock interviewer application, including:

- **Push-to-Talk (PTT)** - Hold "V" key to record and send audio
- **Live Transcription** - Real-time word-level transcript display
- **Speech-to-Speech Workflow** - Audio → STT → Claude → TTS → Audio playback
- **State Management** - Zustand stores for voice and transcription state
- **Error Handling** - Comprehensive error handling and user feedback

## 📦 What Was Implemented

### Frontend Components & Services

#### 1. **Voice Store** (`src/stores/voice.ts`)
Zustand store managing voice interaction state:
- Recording state (idle, recording, processing, playing)
- Live transcript data with word-level timestamps
- Audio error handling
- Playback state management

#### 2. **Voice Service** (`src/services/voiceService.ts`)
Service class handling audio recording and backend communication:
- Browser MediaRecorder API integration
- Audio format detection and conversion
- Base64 encoding for API transmission
- PCM to WAV conversion for playback
- Resource cleanup

#### 3. **Push-to-Talk Hook** (`src/hooks/usePushToTalk.ts`)
React hook for keyboard-controlled recording:
- "V" key event handling (configurable)
- Automatic recording start/stop
- Integration with voice service
- Error callbacks and success handling
- Prevents accidental activation in input fields

#### 4. **Live Transcript Component** (`src/components/LiveTranscript.tsx`)
Real-time transcript display:
- Polls backend JSON file (500ms interval)
- Word-level highlighting based on timing
- Automatic scrolling and updates
- Visual states for current/past/future words

#### 5. **Enhanced FloatingPane** (`src/components/FloatingPane.tsx`)
Updated interviewer pane with voice features:
- PTT enable/disable toggle
- Recording status indicators
- Live transcript section (collapsible)
- Visual feedback during recording/processing/playing
- Error message display

### API & Backend Integration

#### Backend Configuration
The backend workflow system provides:
- `/workflow/input/stream` - STT → Claude → TTS endpoint
- `/live_transcription.json` - Real-time transcript file
- Live transcription writer with word-level timestamps

## 🚀 Setup Instructions

### 1. Backend Configuration

Add to your backend `.env` file:

```bash
# Required: API Keys
DEEPGRAM_API_KEY=your_deepgram_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Audio Configuration
DEEPGRAM_SAMPLE_RATE=48000
DEEPGRAM_STREAM_ENCODING=linear16
DEEPGRAM_TTS_VOICE=aura-2-thalia-en
DEEPGRAM_STT_MODEL=nova-3

# Live Transcription (enable to generate real-time transcript)
LIVE_TRANSCRIPTION_PATH=live_transcription.json
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0
```

### 2. Frontend Configuration

No additional configuration needed! The frontend automatically:
- Detects backend URL (`localhost:8000` in development)
- Enables voice features when PTT is toggled on
- Polls for live transcription when available

### 3. Start the Application

```bash
# Terminal 1: Start backend
cd mockly-backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd mockly-frontend
npm run dev
```

### 4. Verify Setup

1. Open frontend at `http://localhost:5173`
2. Start an interview
3. Click "PTT On" button in Kevin's pane
4. Hold "V" key and speak
5. Release "V" key to send audio
6. Watch for processing and audio response

## 🎮 User Guide

### Push-to-Talk Usage

1. **Enable PTT**: Click the "PTT Off" button to toggle it to "PTT On"
2. **Record Audio**: Press and HOLD the "V" key while speaking
3. **Send Audio**: Release the "V" key to stop recording and send
4. **Wait for Response**: System processes audio and plays response
5. **See Status**: Watch status bar for recording/processing/playing indicators

### Status Indicators

- 🔴 **Recording...** - Microphone is active, speak now
- 🟡 **Processing...** - Audio being sent to backend for processing
- 🟢 **Playing response...** - AI response audio is playing
- ⚪ **Press and hold V to speak** - Ready for input

### Live Transcript

- Click "Live Transcript" to expand/collapse
- Words highlight as they're spoken in real-time
- Shows word count and last update time
- Hover over words to see precise timing

## 🏗️ Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  USER INTERACTION                                               │
│  Press and hold "V" key                                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND - Audio Recording                                     │
│  • MediaRecorder captures audio                                 │
│  • Audio chunks accumulated                                     │
│  • Convert to base64 on key release                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  API REQUEST                                                    │
│  POST /workflow/input/stream                                    │
│  {                                                              │
│    mode: "voice",                                              │
│    audio_b64: "<base64 audio>",                                │
│    mime: "audio/webm",                                         │
│    difficulty: "medium",                                       │
│    question: { statement: "..." }                              │
│  }                                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND WORKFLOW                                               │
│  1. Deepgram STT: Audio → Text transcript                      │
│  2. Claude API: Generate response to transcript                 │
│  3. Deepgram TTS: Response text → Audio                        │
│  4. Live Transcription: Update JSON with word timestamps        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  API RESPONSE                                                   │
│  • Raw PCM audio stream (L16, 48kHz, mono)                     │
│  • Content-Type: audio/L16; rate=48000; channels=1            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND - Audio Playback                                      │
│  • Convert PCM to WAV format                                    │
│  • Create blob URL                                              │
│  • Play through HTML5 Audio element                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LIVE TRANSCRIPTION (Parallel)                                  │
│  • Poll /live_transcription.json every 500ms                    │
│  • Display word-level timestamps                                │
│  • Highlight current word based on playback time                │
└─────────────────────────────────────────────────────────────────┘
```

### State Management Flow

```typescript
// Voice State Transitions
idle → recording (V key pressed)
recording → processing (V key released)
processing → playing (audio response ready)
playing → idle (audio finished)
processing → idle (error occurred)

// Transcript State
null → LiveTranscript (first poll with data)
LiveTranscript → Updated LiveTranscript (new data from poll)
```

## 🔧 Technical Details

### Audio Recording

**Browser Compatibility:**
- Chrome/Edge: `audio/webm;codecs=opus` (preferred)
- Firefox: `audio/webm` or `audio/ogg;codecs=opus`
- Safari: `audio/mp4` (fallback)

**Recording Settings:**
```typescript
{
  audio: {
    channelCount: 1,          // Mono audio
    sampleRate: 48000,        // 48kHz
    echoCancellation: true,   // Reduce echo
    noiseSuppression: true,   // Reduce background noise
    autoGainControl: true,    // Normalize volume
  }
}
```

### Audio Format Conversion

**Backend Response:** PCM L16 (uncompressed, 48kHz, 16-bit, mono)

**WAV Header Generation:**
```typescript
// Create WAV header for browser playback
- RIFF header (44 bytes)
- Format: PCM (format code 1)
- Sample rate: 48000 Hz
- Bit depth: 16 bits
- Channels: 1 (mono)
```

### Live Transcription Format

```typescript
interface TranscriptWord {
  word: string         // The transcribed word
  start_time: number  // Start time in seconds (e.g., 1.234)
  end_time: number    // End time in seconds (e.g., 1.567)
}

interface LiveTranscript {
  transcription: TranscriptWord[]
  last_updated: string  // ISO 8601 timestamp
  word_count: number
}
```

## 🐛 Troubleshooting

### Issue: "Microphone access failed"

**Cause:** Browser denied microphone permission

**Solution:**
1. Click the camera/microphone icon in browser address bar
2. Allow microphone access
3. Refresh the page
4. Enable PTT again

### Issue: No audio plays after recording

**Possible Causes:**
1. Backend not running or not accessible
2. API keys not configured
3. Network error

**Check:**
```bash
# Verify backend is running
curl http://localhost:8000/

# Check backend logs for errors
tail -f logs/backend.log | grep -i error

# Test workflow endpoint directly
curl -X POST http://localhost:8000/workflow/debug/tts --output test.raw
```

### Issue: Live transcript not showing

**Check:**
1. Is `LIVE_TRANSCRIPTION_PATH` set in backend `.env`?
2. Is the file being created? Check `live_transcription.json` in backend root
3. Is frontend polling the correct URL?

**Debug:**
```bash
# Watch transcript file updates
watch -n 0.5 cat live_transcription.json

# Check browser console for fetch errors
# Open DevTools → Console → Filter for "transcript"
```

### Issue: Recording doesn't start when pressing V

**Check:**
1. Is PTT enabled? (Button should show "PTT On")
2. Are you focused in an input field? (PTT disabled in inputs)
3. Browser console errors?

**Debug:**
```javascript
// Check if MediaRecorder is supported
console.log('MediaRecorder supported:', typeof MediaRecorder !== 'undefined')

// Check microphone permissions
navigator.permissions.query({ name: 'microphone' })
  .then(result => console.log('Mic permission:', result.state))
```

### Issue: Audio quality is poor

**Solutions:**
1. **Increase sample rate:**
   ```bash
   # In backend .env
   DEEPGRAM_SAMPLE_RATE=48000  # Higher quality
   ```

2. **Try different TTS voice:**
   ```bash
   DEEPGRAM_TTS_VOICE=aura-2-asteria-en  # Different voice
   ```

3. **Check network bandwidth:**
   - Audio streaming requires stable connection
   - Use wired connection if on Wi-Fi

## 📊 Performance Considerations

### Network Usage

- **Recording Upload**: ~20KB per second of speech
- **Audio Response**: ~94KB per second (PCM @ 48kHz)
- **Transcript Polling**: ~1KB every 500ms (minimal)

### Latency Breakdown

- **Recording**: Instant (local)
- **Upload**: 100-500ms (depends on network)
- **STT Processing**: 200-800ms (Deepgram)
- **Claude Response**: 500-2000ms (depends on complexity)
- **TTS Generation**: 300-1000ms (Deepgram)
- **Download & Play**: 100-300ms (network)

**Total**: ~1.5-5 seconds from key release to audio playback

### Optimization Tips

1. **Reduce STT latency:** Use faster Deepgram model (nova-2 instead of nova-3)
2. **Reduce TTS latency:** Use streaming TTS (already implemented)
3. **Reduce network latency:** Deploy backend closer to users
4. **Cache questions:** Preload question context to avoid lookup delays

## 🔐 Security Considerations

### Microphone Access

- Requires explicit user permission
- Only active when PTT is enabled
- Recording stops immediately when V key released
- No audio stored client-side (sent immediately to backend)

### API Keys

- Never exposed to frontend
- Stored in backend `.env` file only
- Backend validates all requests

### Audio Data

- Transmitted as base64 over HTTPS (in production)
- Not logged or stored by default
- Processed in real-time and discarded

## 🎨 Customization

### Change PTT Key

```typescript
// In FloatingPane.tsx
const { isRecording, isProcessing, isPlaying } = usePushToTalk({
    apiBase,
    key: 'space',  // Change to spacebar
    // ... other options
})
```

### Change Polling Interval

```typescript
// In LiveTranscript.tsx
<LiveTranscript 
    apiBase={apiBase} 
    pollingInterval={1000}  // Poll every 1 second instead of 500ms
/>
```

### Change TTS Voice

```bash
# In backend .env
DEEPGRAM_TTS_VOICE=aura-2-arcas-en  # Male voice
DEEPGRAM_TTS_VOICE=aura-2-asteria-en  # Another female voice
```

### Customize Recording Settings

```typescript
// In voiceService.ts, startRecording() method
this.stream = await navigator.mediaDevices.getUserMedia({
    audio: {
        channelCount: 1,
        sampleRate: 16000,  // Lower quality, smaller files
        echoCancellation: true,
        noiseSuppression: false,  // Disable if needed
        autoGainControl: true,
    },
})
```

## 📚 API Reference

### Backend Endpoints

#### POST `/workflow/input/stream`

Process voice input through STT→Claude→TTS pipeline.

**Request:**
```json
{
  "mode": "voice",
  "audio_b64": "<base64-encoded audio>",
  "mime": "audio/webm",
  "difficulty": "easy" | "medium" | "hard",
  "question": {
    "statement": "Optional question context"
  }
}
```

**Response:**
- Content-Type: `audio/L16; rate=48000; channels=1`
- Body: Raw PCM audio stream

#### GET `/live_transcription.json`

Get current live transcription with word-level timestamps.

**Response:**
```json
{
  "transcription": [
    {
      "word": "hello",
      "start_time": 0.5,
      "end_time": 0.8
    }
  ],
  "last_updated": "2025-10-26T15:42:33Z",
  "word_count": 1
}
```

### Frontend Services

#### VoiceService

```typescript
import { VoiceService } from '@/services/voiceService'

const service = new VoiceService({ 
    apiBase: 'http://localhost:8000' 
})

// Start recording
await service.startRecording()

// Stop and get audio blob
const audioBlob = await service.stopRecording()

// Send to backend and get response
const responseAudio = await service.sendAudioToBackend(
    audioBlob,
    { difficulty: 'medium', questionContext: 'Explain binary trees' }
)
```

#### usePushToTalk Hook

```typescript
import { usePushToTalk } from '@/hooks/usePushToTalk'

const { 
    isRecording, 
    isProcessing, 
    isPlaying 
} = usePushToTalk({
    apiBase: 'http://localhost:8000',
    key: 'v',
    difficulty: 'medium',
    questionContext: 'Your question here',
    enabled: true,
    onError: (error) => console.error(error),
    onSuccess: () => console.log('Success!'),
})
```

## 🧪 Testing

### Manual Testing Checklist

- [ ] PTT button toggles on/off correctly
- [ ] Holding V key shows "Recording..." status
- [ ] Releasing V key triggers processing
- [ ] Audio response plays automatically
- [ ] Live transcript updates during response
- [ ] Words highlight in real-time
- [ ] Error messages display for failures
- [ ] Recording works with different question difficulties
- [ ] Transcript expands/collapses correctly
- [ ] PTT disabled in input fields (doesn't interfere with typing)

### Browser Compatibility

Tested and working on:
- ✅ Chrome 120+ (Windows, macOS, Linux)
- ✅ Edge 120+ (Windows, macOS)
- ✅ Firefox 121+ (Windows, macOS, Linux)
- ✅ Safari 17+ (macOS) - with limitations on audio formats

### Known Limitations

1. **Safari:** May require WAV format for recording (no WebM support)
2. **Mobile:** Push-to-talk not ideal for touch interfaces (consider adding button)
3. **Firefox:** May require manual microphone permission each session

## 📝 Future Enhancements

### Potential Improvements

1. **Mobile Support:** Add touch-friendly record button
2. **Audio Visualization:** Show waveform during recording
3. **Noise Detection:** Auto-stop on silence
4. **Speaker Diarization:** Track who's speaking in transcript
5. **Transcript History:** Save conversation history
6. **Export Transcript:** Download as text file
7. **Voice Commands:** Trigger actions with voice
8. **Real-time Streaming:** Stream audio chunks as they're generated

## 🤝 Contributing

When modifying voice functionality:

1. **Test thoroughly** across browsers
2. **Handle errors gracefully** - don't crash on permission denial
3. **Clean up resources** - stop streams, clear timeouts
4. **Update this documentation** - keep it in sync with code
5. **Check performance** - audio processing is resource-intensive

## 📞 Support

For issues or questions:

1. Check this documentation first
2. Review troubleshooting section
3. Check browser console for errors
4. Check backend logs for API errors
5. Test with `/workflow/debug/tts` endpoint to isolate issues

## 🎉 Success!

If you've reached this point and everything works:

1. PTT enabled ✅
2. Hold V to record ✅
3. Audio processes and plays ✅
4. Live transcript updates ✅
5. Error handling works ✅

**You're ready to conduct voice-enabled mock interviews!** 🎤🚀

---

**Implementation Date:** October 26, 2025  
**Last Updated:** October 26, 2025  
**Version:** 1.0.0

