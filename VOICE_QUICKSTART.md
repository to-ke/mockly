# 🎤 Voice Features - Quick Start Guide

## ⚡ 5-Minute Setup

### 1. Configure Backend (.env)

```bash
cd mockly-backend

# Add these to your .env file:
DEEPGRAM_API_KEY=your_deepgram_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
LIVE_TRANSCRIPTION_PATH=live_transcription.json
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0
```

### 2. Start Services

```bash
# Terminal 1: Backend
cd mockly-backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend  
cd mockly-frontend
npm run dev
```

### 3. Use Voice Features

1. Open `http://localhost:5173`
2. Start an interview
3. Look for Kevin's floating pane (interviewer)
4. Click **"PTT Off"** to toggle to **"PTT On"**
5. Press and HOLD **"V"** key while speaking
6. Release **"V"** to stop and send
7. Wait for AI response to play
8. Click **"Live Transcript"** to see word-level timing

## 🎮 Controls

| Action | Key/Button | Result |
|--------|-----------|--------|
| Enable PTT | Click "PTT Off" | Toggles to "PTT On" |
| Start Recording | Hold "V" key | 🔴 Recording indicator |
| Stop & Send | Release "V" | 🟡 Processing starts |
| View Transcript | Click "Live Transcript" | Expands transcript section |

## 🔍 Status Indicators

- 🔴 **Recording...** - Speak now!
- 🟡 **Processing...** - AI is thinking
- 🟢 **Playing response...** - Listen to AI
- ⚪ **Press and hold V to speak** - Ready

## 🐛 Troubleshooting

### Can't record?
- Allow microphone permission in browser
- Check "PTT On" is enabled
- Make sure you're not focused in an input field

### No audio plays?
```bash
# Test backend
curl -X POST http://localhost:8000/workflow/debug/tts --output test.raw

# Check logs
tail -f mockly-backend/logs/*.log
```

### No live transcript?
```bash
# Check file is created
ls mockly-backend/live_transcription.json

# Watch for updates
watch -n 0.5 cat mockly-backend/live_transcription.json
```

## 📚 Full Documentation

- **Complete Guide:** [`VOICE_INTEGRATION_GUIDE.md`](./VOICE_INTEGRATION_GUIDE.md)
- **Implementation Details:** [`VOICE_IMPLEMENTATION_SUMMARY.md`](./VOICE_IMPLEMENTATION_SUMMARY.md)

## ✅ Quick Test

```bash
# 1. Start backend and frontend (see above)

# 2. In browser:
#    - Start interview
#    - Enable PTT
#    - Hold V and say "Hello"
#    - Release V

# 3. You should see:
#    - 🔴 Recording indicator while holding V
#    - 🟡 Processing after release
#    - 🟢 Audio plays back
#    - Transcript updates (if expanded)
```

## 🎉 Success!

If everything works, you now have:
- ✅ Push-to-talk voice input
- ✅ AI-powered responses
- ✅ Live word-level transcription
- ✅ Seamless voice/text interaction

**Happy interviewing!** 🚀

