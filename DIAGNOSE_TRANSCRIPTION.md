# 🔍 Diagnose: Live Transcription Not Appearing in Logs

## Current Situation

You're seeing TTS audio logs but NO LiveTranscription logs:
```
✅ [Deepgram TTS raw] Large gap detected: ...  (TTS is working)
❌ NO [LiveTranscription] logs at all
```

This means transcription is either:
1. Not initialized (LIVE_TRANSCRIPTION_PATH issue)
2. Initialization failed silently
3. Encoding mismatch

## Fix Applied

I've added **diagnostic logging** that will tell us exactly what's wrong.

### New Logs to Look For

After restarting, you'll see **ONE** of these:

**Option 1: Transcription Enabled ✅**
```
[Deepgram TTS raw] ✅ Live transcription ENABLED: path=live_transcription.json, encoding=linear16
```
Then when audio arrives:
```
[LiveTranscription] Buffer: X bytes
```

**Option 2: Path Not Set ⚠️**
```
[Deepgram TTS raw] Live transcription DISABLED: LIVE_TRANSCRIPTION_PATH not set
```
**Fix:** Add to your `.env`:
```bash
LIVE_TRANSCRIPTION_PATH=live_transcription.json
```

**Option 3: Initialization Failed ❌**
```
[Deepgram TTS raw] ❌ Failed to init transcription: [error details]
```
**Fix:** Check the error message for details

**Option 4: Wrong Encoding ⚠️**
```
[Deepgram TTS raw] Transcription not initialized - check LIVE_TRANSCRIPTION_PATH
# OR
[Deepgram TTS raw] Wrong encoding for transcription: mulaw (need linear16)
```
**Fix:** Set in `.env`:
```bash
DEEPGRAM_STREAM_ENCODING=linear16
```

## Steps to Diagnose

### 1. Restart Backend

```bash
cd mockly-backend
poetry run python -m app.main
```

### 2. Generate Audio

Ask a question or trigger TTS in your app.

### 3. Check Logs Immediately

Look for the initialization log:
```
[Deepgram TTS raw] ✅ Live transcription ENABLED...
```

### 4. Check Config

If you see "DISABLED" or no log at all:

```bash
# Check your environment
cd mockly-backend
python3 -c "from app.services.workflow.config import LIVE_TRANSCRIPTION_PATH, DEEPGRAM_STREAM_ENCODING; print(f'Path: {LIVE_TRANSCRIPTION_PATH}'); print(f'Encoding: {DEEPGRAM_STREAM_ENCODING}')"
```

**Expected output:**
```
Path: live_transcription.json
Encoding: linear16
```

### 5. Verify .env File

Check your `.env` file:

```bash
cat mockly-backend/.env | grep -E "(LIVE_TRANSCRIPTION|DEEPGRAM_STREAM_ENCODING)"
```

Should show:
```bash
DEEPGRAM_STREAM_ENCODING=linear16
LIVE_TRANSCRIPTION_PATH=live_transcription.json  # Optional (has default)
```

## Quick Fixes

### If Path Not Set

Add to `mockly-backend/.env`:
```bash
LIVE_TRANSCRIPTION_PATH=live_transcription.json
```

### If Wrong Encoding

Change in `mockly-backend/.env`:
```bash
DEEPGRAM_STREAM_ENCODING=linear16  # Must be linear16, not mulaw or alaw
```

### If Initialization Fails

Check file permissions:
```bash
# Backend must be able to write to this location
touch live_transcription.json
chmod 644 live_transcription.json
```

## Expected Flow After Fix

```
1. Backend starts
   ↓
2. TTS triggered
   ↓
3. [Deepgram TTS raw] ✅ Live transcription ENABLED: path=live_transcription.json
   ↓
4. Audio arrives
   ↓
5. [LiveTranscription] Buffer: 50000 bytes (0.5s total audio)
   ↓
6. [LiveTranscription] Buffer: 100000 bytes (1.0s total audio)
   ↓
7. [LiveTranscription] Buffer: 192000 bytes (2.0s total audio)
   ↓
8. [LiveTranscription] Triggering transcription: 192000 bytes
   ↓
9. [LiveTranscription] Deepgram response status: 200
   ↓
10. [LiveTranscription] Transcript received: 'actual text...'
    ↓
11. [LiveTranscription] Extracted 15 words
    ↓
    ✅ SUCCESS!
```

## Common Issues

### Issue 1: Docker/Environment Variables

If running in Docker, environment variables might not be passed through.

**Check docker-compose.yml:**
```yaml
services:
  backend:
    environment:
      - LIVE_TRANSCRIPTION_PATH=live_transcription.json
      - DEEPGRAM_STREAM_ENCODING=linear16
```

Or use `.env` file:
```yaml
services:
  backend:
    env_file:
      - .env
```

### Issue 2: Path Issues

If you see "Failed to init transcription: Permission denied"

**Fix:**
```bash
# Make sure directory is writable
cd mockly-backend
mkdir -p $(dirname live_transcription.json)
chmod 755 $(dirname live_transcription.json)
```

### Issue 3: Import Error

If you see "Failed to init transcription: No module named..."

**Fix:**
```bash
cd mockly-backend
poetry install  # Ensure all dependencies installed
```

## After Restart: What to Report

Please share these specific logs after restart:

1. **Initialization log:**
```
[Deepgram TTS raw] ✅ Live transcription ENABLED...
# OR
[Deepgram TTS raw] Live transcription DISABLED...
```

2. **First audio chunk log:**
```
[Deepgram TTS raw] Transcription not initialized...
# OR
[LiveTranscription] Buffer: X bytes
```

3. **Config check output:**
```bash
python3 -c "from app.services.workflow.config import LIVE_TRANSCRIPTION_PATH, DEEPGRAM_STREAM_ENCODING; print(f'Path: {LIVE_TRANSCRIPTION_PATH}'); print(f'Encoding: {DEEPGRAM_STREAM_ENCODING}')"
```

This will tell us exactly what's wrong! 🎯

---

**Restart now and share the new logs!**

