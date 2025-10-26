# 🔧 Auto-Intro Feature - Fixes & Testing Guide

## 🐛 Issues Fixed

### Issue 1: 404 Not Found - `/workflow/type/stream`
**Problem:** Backend returning 404 for `/workflow/type/stream`

**Root Cause:** The workflow router didn't have a `/workflow` prefix, so routes were at root level (e.g., `/type/stream` instead of `/workflow/type/stream`)

**Fix Applied:**
```python
# File: mockly-backend/app/services/workflow/router.py
# Changed from:
router = APIRouter(tags=["workflow"])

# To:
router = APIRouter(prefix="/workflow", tags=["workflow"])
```

**Result:** Routes are now accessible at:
- `/workflow/type/stream` ✅
- `/workflow/input/stream` ✅
- `/workflow/debug/tts` ✅
- etc.

---

### Issue 2: Live Transcription File Not Accessible
**Problem:** Frontend couldn't fetch `live_transcription.json` file

**Root Cause:** No endpoint to serve the transcription file

**Fix Applied:**
```python
# File: mockly-backend/app/main.py
# Added new endpoint:
@app.get("/live_transcription.json")
async def get_live_transcription():
    # Serves the live transcription file with proper headers
```

**Result:** Transcription file now accessible at:
- `http://localhost:8000/live_transcription.json` ✅

---

## ✅ Complete Testing Checklist

### Prerequisites

**Backend Environment:**
```bash
cd mockly-backend

# Verify .env file has these set:
# DEEPGRAM_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
# LIVE_TRANSCRIPTION_PATH=live_transcription.json
# LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0
```

**Frontend:**
```bash
cd mockly-frontend
# No additional config needed
```

---

### Test 1: Backend Routes Are Accessible

```bash
# Terminal 1: Start backend
cd mockly-backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Test endpoints
curl http://localhost:8000/
# Expected: {"ok":true,"service":"Mockly"}

curl -X POST http://localhost:8000/workflow/debug/tts --output test_audio.raw
# Expected: Audio file downloaded (~30KB)

curl http://localhost:8000/live_transcription.json
# Expected: 404 initially (file created on first TTS request) OR JSON if exists
```

**✅ Pass Criteria:**
- Root endpoint returns JSON
- `/workflow/debug/tts` returns audio data
- No 404 errors for `/workflow/...` routes

---

### Test 2: Frontend Can Reach Backend

```bash
# Terminal 1: Backend running (from Test 1)

# Terminal 2: Start frontend
cd mockly-frontend
npm run dev

# Open browser at: http://localhost:5173

# Open Browser DevTools (F12) → Network tab
# Check that requests to localhost:8000 are working
```

**✅ Pass Criteria:**
- Frontend loads without errors
- No CORS errors in console
- Network tab shows successful connections to backend

---

### Test 3: Auto-Intro Feature (Main Test)

**Steps:**

1. **Start Both Services:**
   ```bash
   # Terminal 1: Backend
   cd mockly-backend
   uvicorn app.main:app --reload

   # Terminal 2: Frontend
   cd mockly-frontend
   npm run dev
   ```

2. **Open Browser:**
   - Navigate to `http://localhost:5173`
   - Open DevTools Console (F12)
   - Switch to Console tab

3. **Start Interview:**
   - Select difficulty: **Medium**
   - Click **"Start Interview"**
   - Watch Kevin's floating pane (right side)

4. **Expected Behavior:**

   **Phase 1: Loading (1-2 seconds)**
   - Question loads in code editor
   - Kevin's pane appears

   **Phase 2: Intro Starts (immediately after)**
   - Chat message: "🎙️ Starting interview..."
   - Status bar shows: "🔵 Introducing the problem..."
   - Blue pulsing indicator visible

   **Phase 3: Audio Plays (3-8 seconds)**
   - Audio plays from speakers/headphones
   - Kevin introduces the problem
   - Live transcript updates (if you expand it)

   **Phase 4: Complete**
   - Chat message: "Ready to help! You can ask questions..."
   - Status bar disappears or shows "Press and hold V to speak"
   - Audio has finished playing

**✅ Pass Criteria:**
- No "Failed to fetch" errors in chat
- Audio plays automatically
- Status indicators change correctly
- Can use PTT after intro completes

---

### Test 4: Live Transcription Works

**Steps:**

1. **Enable Live Transcription:**
   - Ensure backend `.env` has: `LIVE_TRANSCRIPTION_PATH=live_transcription.json`

2. **Start Interview:**
   - Follow Test 3 steps 1-3

3. **Expand Transcript:**
   - While intro audio is playing
   - Click **"Live Transcript"** in Kevin's pane
   - Watch for words to appear

4. **Expected Behavior:**
   - Transcript section expands
   - Words appear as audio plays
   - Current word highlights in blue/green
   - Word count updates
   - Timestamps visible on hover

**✅ Pass Criteria:**
- Transcript shows words in real-time
- Word highlighting works
- No errors fetching transcription file

---

### Test 5: PTT After Intro

**Steps:**

1. **Wait for Intro to Complete:**
   - Follow Test 3, wait for audio to finish

2. **Enable PTT:**
   - Click **"PTT Off"** button
   - It should toggle to **"PTT On"**

3. **Test Voice Input:**
   - Hold **"V"** key
   - Say: "Can you explain the problem again?"
   - Release **"V"** key

4. **Expected Behavior:**
   - Shows "🔴 Recording..." while holding V
   - Shows "🟡 Processing..." after release
   - Shows "🟢 Playing response..." when audio plays
   - Hears AI response

**✅ Pass Criteria:**
- PTT works after intro
- No interference between intro and PTT
- Can have voice conversation

---

### Test 6: Error Handling

**Test 6a: Backend Offline**

```bash
# Stop backend (Ctrl+C)
# Frontend still running

# Try starting interview:
```

**Expected:**
- Chat shows: "⚠️ Couldn't play introduction: Failed to fetch..."
- Can still use text chat
- No crashes or blank screens

**Test 6b: Invalid API Keys**

```bash
# Edit mockly-backend/.env
# Set: DEEPGRAM_API_KEY=invalid_key

# Restart backend and test
```

**Expected:**
- Error message in chat
- Graceful fallback
- App still usable

**✅ Pass Criteria:**
- Errors are user-friendly
- No crashes or hangs
- Can recover and continue

---

## 🔍 Troubleshooting

### Problem: Still getting 404 errors

**Check:**
```bash
# Verify backend logs show the route is registered
cd mockly-backend
python -c "
from app.main import app
for route in app.routes:
    if hasattr(route, 'path'):
        print(route.path)
" 2>/dev/null | grep workflow
```

**Expected output:**
```
/workflow/type/stream
/workflow/debug/tts
/workflow/input/stream
...
```

**Fix:** 
- Restart backend: `uvicorn app.main:app --reload`
- Clear browser cache
- Check no proxy interfering

---

### Problem: "Failed to fetch" in browser

**Check:**
```bash
# Open Browser DevTools → Network tab
# Look for failed requests
# Check the URL being called
```

**Common Issues:**
1. **Wrong URL**: Should be `http://localhost:8000/workflow/type/stream`
2. **CORS error**: Check backend CORS settings
3. **Backend not running**: Verify `curl http://localhost:8000/`

**Fix:**
```bash
# Verify backend is accessible
curl http://localhost:8000/workflow/debug/tts --output test.raw
# If this works, frontend should work too
```

---

### Problem: Audio doesn't play

**Check:**
1. **Browser audio permissions**: Allow audio autoplay
2. **Audio format**: Check console for conversion errors
3. **Backend response**: Verify audio data is returned

**Debug:**
```javascript
// In browser console
localStorage.setItem('debug', 'true')
// Reload page, try again, check console
```

**Fix:**
- Try different browser (Chrome/Firefox)
- Check audio output device
- Verify backend returns audio: `curl ... --output test.raw` then check file size

---

### Problem: Live transcript not showing

**Check:**
```bash
# Verify file is created
cd mockly-backend
ls -lh live_transcription.json

# Try fetching directly
curl http://localhost:8000/live_transcription.json
```

**Expected:** JSON with transcription data

**Fix:**
- Ensure `LIVE_TRANSCRIPTION_PATH=live_transcription.json` in .env
- Restart backend
- Wait for first TTS request (file created on-demand)

---

## 📊 Success Indicators

### Backend Logs (Should See):
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
...
INFO:     172.18.0.1:XXXXX - "POST /workflow/type/stream HTTP/1.1" 200 OK
```

**Note:** Should be `200 OK`, not `404 Not Found`

### Frontend Console (Should See):
```
[Mockly] Interview intro triggered
[Audio] Playing intro audio...
[Transcript] Updated with 15 words
[Audio] Intro complete
```

**Note:** No "Failed to fetch" errors

### Browser Network Tab (Should See):
```
POST /workflow/type/stream   200   3.5s   audio/L16...
GET  /live_transcription.json 200   10ms   application/json
```

---

## 🎯 Complete Test Sequence

**Full end-to-end test:**

```bash
# 1. Setup
cd mockly-backend
# Verify .env has API keys
uvicorn app.main:app --reload &
cd ../mockly-frontend
npm run dev &

# 2. Wait for both to start (~5-10 seconds)

# 3. Open browser
# Navigate to: http://localhost:5173

# 4. Test flow
# - Select "Medium" difficulty
# - Click "Start Interview"
# - Watch for blue indicator
# - Listen for audio
# - Check chat for messages
# - Expand live transcript
# - Enable PTT after intro
# - Hold V and speak
# - Verify response plays

# 5. Verify logs
# Backend logs should show:
#   - POST /workflow/type/stream 200 OK
#   - [Deepgram WS] SENT Speak
#   - [LiveTranscription] Updated with X words

# Frontend console should show:
#   - No errors
#   - Audio playing
#   - Transcript updating
```

**✅ All Green:** Feature working correctly!

---

## 📝 Quick Verification Commands

```bash
# Verify backend routes
curl http://localhost:8000/ | jq .
curl -X POST http://localhost:8000/workflow/debug/tts -o test.raw && ls -lh test.raw

# Verify transcription endpoint
curl http://localhost:8000/live_transcription.json | jq .

# Check frontend build
cd mockly-frontend
npm run lint

# Check backend syntax
cd mockly-backend
python -m py_compile app/main.py app/services/workflow/router.py
```

---

## 🎉 Success!

If all tests pass, you now have:
✅ Automatic interview introduction  
✅ Voice-enabled interview  
✅ Live transcription  
✅ Push-to-talk functionality  
✅ Error recovery  
✅ Complete end-to-end workflow  

**The interview experience is complete!** 🚀

---

## 📞 Need Help?

**Check in order:**
1. This document's troubleshooting section
2. Backend logs: `tail -f logs/*.log` (if logging enabled)
3. Browser console for frontend errors
4. Network tab for failed requests

**Common fixes:**
- Restart backend: `Ctrl+C` then `uvicorn...` again
- Clear browser cache: `Ctrl+Shift+R`
- Check `.env` file has all required keys
- Verify network connectivity: `ping localhost`

---

**Last Updated:** 2025-10-26  
**Status:** ✅ Ready for Testing

