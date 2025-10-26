# 🔧 Fix: "No words in Deepgram response"

## Problem

Getting these warnings:
```
WARNING:root:[LiveTranscription] No words in Deepgram response
WARNING:root:[LiveTranscription] No words received from transcription
```

But no HTTP errors - Deepgram is responding successfully.

## Root Causes

This usually means one of these issues:

### 1. Not Enough Audio Buffered ⚠️
- Deepgram needs at least **2 seconds of audio** for reliable transcription
- Shorter audio may not transcribe properly

### 2. Silent Audio 🔇
- The audio being transcribed is actually silent (no speech)
- This happens if TTS hasn't started yet or audio is corrupted

### 3. Timing Issue ⏱️
- Transcription triggered too early (before audio fully arrives)
- Buffer accumulating but not reaching threshold

## Fixes Applied

### Fix 1: Increased Minimum Audio Buffer

**File:** `mockly-backend/app/services/workflow/live_transcription.py`

**Changed:**
```python
# Before
min_audio_bytes: int = 96000,  # ~1 second

# After
min_audio_bytes: int = 192000,  # ~2 seconds (more reliable)
```

**Why:** Deepgram works better with longer audio segments.

### Fix 2: Enhanced Debug Logging

Added comprehensive logging to track:
- Buffer size as audio accumulates
- Exact Deepgram response structure
- Audio duration being transcribed
- Whether transcript is empty

**New logs you'll see:**
```
[LiveTranscription] Buffer: 50000 bytes (0.5s total audio)
[LiveTranscription] Buffer: 100000 bytes (1.0s total audio)
[LiveTranscription] Buffer: 192000 bytes (2.0s total audio)
[LiveTranscription] Triggering transcription: 192000 bytes
[LiveTranscription] Transcript received: 'Hello, I'm here to help you...'
```

### Fix 3: Better Error Messages

Now logs:
- Empty transcript warning with audio duration
- Full Deepgram response when debugging
- Specific reasons why no words were returned

## Testing After Fix

### 1. Restart Backend

```bash
cd mockly-backend
poetry run python -m app.main
```

### 2. Generate TTS Audio

Trigger audio in your app (ask a question).

### 3. Check Logs for These Patterns

**Pattern 1: Buffer Accumulating (Good)**
```
[LiveTranscription] Buffer: 50000 bytes (0.5s total audio)
[LiveTranscription] Buffer: 100000 bytes (1.0s total audio)
[LiveTranscription] Buffer: 192000 bytes (2.0s total audio)
[LiveTranscription] Triggering transcription: 192000 bytes, 2.0s since last update
```

**Pattern 2: Successful Transcription (Good)**
```
[LiveTranscription] Transcribing 192000 bytes of audio
[LiveTranscription] Deepgram response status: 200
[LiveTranscription] Transcript received: 'Hello, I'm here to help you with...'
[LiveTranscription] Extracted 15 words
✅ SUCCESS!
```

**Pattern 3: Empty Transcript (Problem)**
```
[LiveTranscription] Transcribing 192000 bytes of audio
[LiveTranscription] Deepgram response status: 200
[LiveTranscription] Transcript received: ''
[LiveTranscription] Empty transcript - audio may be silent or too short
[LiveTranscription] Audio was 192000 bytes = 2.00 seconds at 48kHz
⚠️ ISSUE: Audio is silent
```

**Pattern 4: Not Enough Audio Yet (Normal)**
```
[LiveTranscription] Waiting for more audio: 96000 bytes (need 192000)
⏳ Just needs more time
```

## Troubleshooting

### Scenario 1: Logs show "Empty transcript"

**Problem:** Audio is silent or corrupted

**Check:**
1. Is TTS actually generating audio?
```
# Look for TTS logs
[Deepgram TTS] SENT Speak: "..."
[Deepgram WS] audio X.X KiB
```

2. Is audio reaching the transcription buffer?
```
# Should see buffer logs
[LiveTranscription] Buffer: X bytes
```

**Fix:** 
- Ensure TTS is working (test with audio playback)
- Check `DEEPGRAM_STREAM_ENCODING=linear16` in .env
- Verify audio is not empty/corrupted

### Scenario 2: Logs show "Waiting for more audio"

**Problem:** Not enough audio accumulated yet

**This is normal!** Wait for:
- At least 2 seconds of audio (192000 bytes at 48kHz)
- The `update_interval` to pass (default: 2 seconds)

**To speed up (optional):**
```bash
# In .env - reduce interval
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=1.5
```

### Scenario 3: No buffer logs at all

**Problem:** Audio chunks not being added

**Check:**
1. Is `LiveTranscriptionWriter` initialized?
```
# Look for this log at startup
[Deepgram TTS] Live transcription enabled for lip sync
```

2. Is `add_audio_chunk` being called?
```
# Should see this in tts.py
transcription.add_audio_chunk(frame, _pcm_duration_ms(...))
```

**Fix:**
- Verify tts.py has transcription enabled (not commented out)
- Check that audio chunks are being received from Deepgram TTS

### Scenario 4: Getting partial transcription

**Example:** Only transcribes first few seconds, then stops

**Cause:** Buffer reset too early or timing issue

**Fix:**
- Increase update interval: `LIVE_TRANSCRIPTION_UPDATE_INTERVAL=3.0`
- Check that `finalize()` is being called at end

## Configuration Tuning

### For Faster Updates (More API Calls)

```bash
# In .env
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=1.5  # Update every 1.5 seconds
```

**Note:** Requires at least 192000 bytes buffered (~2 seconds)

### For Longer Audio Segments (Fewer API Calls)

```bash
# In .env
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=5.0  # Wait 5 seconds
```

**Trade-off:** Higher latency but more audio per transcription

### To Debug Audio Issues

Enable debug logging in your backend:

```python
# In app/main.py or at startup
import logging
logging.basicConfig(level=logging.DEBUG)
```

Then look for detailed buffer and audio logs.

## Expected Behavior

After the fixes, you should see:

1. **Audio Accumulation**
```
[LiveTranscription] Buffer: 50000 bytes (0.5s)
[LiveTranscription] Buffer: 100000 bytes (1.0s)
[LiveTranscription] Buffer: 192000 bytes (2.0s)
```

2. **Transcription Trigger**
```
[LiveTranscription] Triggering transcription: 192000 bytes, 2.0s since last update
```

3. **Successful Response**
```
[LiveTranscription] Deepgram response status: 200
[LiveTranscription] Transcript received: 'actual speech text here'
[LiveTranscription] Extracted 15 words
```

4. **File Update**
```
[LiveTranscription] Updated with 15 new words (total: 15)
```

5. **File Creation**
```bash
$ cat live_transcription.json | jq
{
  "transcription": [
    {"word": "Hello", "start_time": 0.0, "end_time": 0.234},
    ...
  ],
  "word_count": 15
}
```

## API Usage Note

Each transcription call costs Deepgram API credits. With the default settings:
- **Update interval:** 2 seconds
- **Buffer size:** ~2 seconds
- **API calls:** ~1 per 2 seconds of TTS audio

For a 10-second TTS response, you'll make ~5 STT API calls.

## Summary of Changes

1. ✅ Increased minimum buffer from 1s to 2s (more reliable)
2. ✅ Added buffer accumulation logging
3. ✅ Added detailed Deepgram response logging
4. ✅ Added empty transcript detection with audio duration
5. ✅ Added full response logging for debugging

## Success Checklist

After restart:

✅ Backend starts with: `[Deepgram TTS] Live transcription enabled for lip sync`  
✅ Buffer logs show audio accumulating: `Buffer: X bytes`  
✅ Transcription triggers: `Triggering transcription: 192000 bytes`  
✅ Deepgram responds: `response status: 200`  
✅ Transcript received: `Transcript received: 'actual text here'`  
✅ Words extracted: `Extracted X words` (X > 0)  
✅ File updated: `live_transcription.json` has words  
✅ Endpoint works: `curl /api/workflow/captions/live` returns words  
✅ Avatar lip syncs when audio plays  

---

**Restart your backend now and watch the logs!** 

The enhanced logging will show you exactly what's happening. 🔍

