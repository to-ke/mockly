# 🔧 Lip Sync Fix - Using Deepgram Live Transcription

## What Was Fixed

The initial implementation used simple text logging instead of actual Deepgram transcription. This has been corrected to use the **existing Deepgram STT system** that provides precise word-level timestamps.

## Changes Made

### 1. Re-enabled Live Transcription in TTS (`tts.py`)
**Status:** ✅ Fixed

Both `stream_deepgram_tts()` and `stream_deepgram_tts_raw()` now initialize `LiveTranscriptionWriter`:

```python
# Before: Transcription was disabled
transcription = None

# After: Transcription enabled for lip sync
transcription = None
if LIVE_TRANSCRIPTION_PATH:
    try:
        transcription = LiveTranscriptionWriter(
            LIVE_TRANSCRIPTION_PATH,
            sample_rate=DEEPGRAM_SAMPLE_RATE,
            encoding=str(DEEPGRAM_STREAM_ENCODING),
            update_interval_seconds=LIVE_TRANSCRIPTION_UPDATE_INTERVAL,
        )
        logging.info("[Deepgram TTS] Live transcription enabled for lip sync")
    except Exception as exc:
        logging.error("[Deepgram TTS] Failed to init transcription: %s", exc)
        transcription = None
```

### 2. Updated Captions Endpoint (`router.py`)
**Status:** ✅ Fixed

The `/api/workflow/captions/live` endpoint now:
- Reads from `LIVE_TRANSCRIPTION_PATH` instead of `TTS_LIVE_JSON_PATH`
- Uses **actual Deepgram STT word timestamps** (not estimated)
- Transforms the format to match frontend expectations

```python
# Reads: live_transcription.json
# Format: {"transcription": [{"word": "...", "start_time": 0.0, "end_time": 0.3}], ...}
# Returns: {"words": [...], "status": "active", ...}
```

## How It Works Now

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Claude generates text → Deepgram TTS creates audio      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. LiveTranscriptionWriter:                                 │
│    - Buffers audio chunks                                   │
│    - Every 2 seconds, sends to Deepgram STT                 │
│    - Gets word-level timestamps                             │
│    - Writes to live_transcription.json                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Frontend polls /api/workflow/captions/live (150ms)      │
│    - Gets real word timestamps from Deepgram STT            │
│    - Syncs mouth with audio.currentTime                     │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
              Avatar lip syncs! 🎉
```

## Key Benefits

### Before (Estimated Timing)
❌ Text chunks with estimated timing (~300ms per word)
❌ No actual audio analysis
❌ Inaccurate for different speaking speeds
❌ Poor sync quality

### After (Deepgram STT)
✅ **Real word timestamps** from Deepgram STT
✅ Precise timing based on actual audio
✅ Adapts to speech rate variations
✅ Professional lip sync quality

## Configuration

Your `.env` should have:

```bash
# Required for lip sync
DEEPGRAM_API_KEY=your_key_here
LIVE_TRANSCRIPTION_PATH=live_transcription.json

# Audio settings
DEEPGRAM_SAMPLE_RATE=48000
DEEPGRAM_STREAM_ENCODING=linear16
DEEPGRAM_TTS_VOICE=aura-2-thalia-en

# Transcription update frequency (default: 2 seconds)
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0
```

**Note:** `LIVE_TRANSCRIPTION_PATH` is already set by default in `config.py`!

## Testing the Fix

### 1. Start Backend
```bash
cd mockly-backend
poetry run python -m app.main
```

**Expected logs:**
```
[Deepgram TTS] Live transcription enabled for lip sync
```

### 2. Generate Audio
Trigger any TTS generation (e.g., ask a question in your app).

**Check transcription file:**
```bash
cat live_transcription.json
```

**Expected format:**
```json
{
  "transcription": [
    {"word": "Hello", "start_time": 0.0, "end_time": 0.234},
    {"word": "world", "start_time": 0.234, "end_time": 0.512}
  ],
  "last_updated": "2024-01-01T12:00:00Z",
  "word_count": 2
}
```

### 3. Test Caption Endpoint
```bash
curl http://localhost:8000/api/workflow/captions/live
```

**Expected response:**
```json
{
  "words": [
    {"word": "Hello", "start_time": 0.0, "end_time": 0.234},
    {"word": "world", "start_time": 0.234, "end_time": 0.512}
  ],
  "status": "active",
  "last_updated": 1234567890.123,
  "word_count": 2
}
```

### 4. Test Frontend
```bash
cd mockly-frontend
npm run dev
```

1. Navigate to your interview screen
2. Use `TalkingHeadSync` component
3. Trigger audio playback
4. **Avatar mouth should now move in sync!** 🎉

## Troubleshooting

### No word timestamps?

**Check 1:** Is transcription enabled?
```bash
# In backend logs, you should see:
[Deepgram TTS] Live transcription enabled for lip sync
```

**Check 2:** Is the file being created?
```bash
ls -la live_transcription.json
```

**Check 3:** Does the file have data?
```bash
cat live_transcription.json | jq '.word_count'
```

### Still no lip movement?

**Check 1:** Frontend polling working?
```javascript
// In browser console:
fetch('/api/workflow/captions/live')
  .then(r => r.json())
  .then(console.log)
  
// Should show words array with timestamps
```

**Check 2:** Audio playing?
```javascript
// Check audio element in TalkingHeadSync
console.log(audioRef.current?.currentTime)
```

**Check 3:** Check browser console for errors
```
Look for: [TalkingHeadSync] errors
```

### Transcription updating slowly?

Adjust the update interval:
```bash
# In .env
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=1.0  # Update every 1 second
```

Lower values = more responsive, but more API calls.

## Performance Considerations

### Deepgram API Usage

The system now makes **STT API calls** to transcribe the generated audio:
- Frequency: Every `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` seconds (default: 2s)
- Cost: Deepgram STT API pricing applies
- Quality: Professional-grade word timing

**Optimization tips:**
1. Increase update interval to 3-5s if you want to reduce API calls
2. Use shorter audio segments for faster updates
3. Monitor your Deepgram usage dashboard

### Memory Usage

- Audio buffer: ~1 second of audio (~96KB at 48kHz)
- JSON file: Small (<1MB even for long conversations)
- No significant memory impact

## Why Re-transcribe TTS Audio?

You might wonder: "Why transcribe audio we just generated from text?"

**Answer:** Because we need **precise word-level timing**, not just the text.

- Deepgram TTS generates audio with variable pacing
- Different words take different amounts of time to speak
- Pauses, emphasis, and natural speech variations
- Only Deepgram STT can give us exact timestamps for each word

This is industry-standard practice for high-quality lip sync!

## Next Steps

1. ✅ Live transcription enabled
2. ✅ Captions endpoint fixed
3. 🎯 Test with your application
4. 🎯 Adjust `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` if needed
5. 🎯 Monitor Deepgram API usage

## Summary

The lip sync system now uses **real Deepgram STT word timestamps** instead of estimated timing. This provides professional-quality synchronization between audio and avatar mouth movements.

**Files modified:**
- `mockly-backend/app/services/workflow/tts.py` - Re-enabled transcription
- `mockly-backend/app/services/workflow/router.py` - Fixed endpoint to read from correct file

**No frontend changes needed** - the `TalkingHeadSync` component already expects the correct format!

---

**Test it now and enjoy precise lip sync!** 🎉

