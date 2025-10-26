# Live Transcription - Quick Reference Card

## 🚀 One-Minute Setup

```bash
# 1. Add to .env
DEEPGRAM_API_KEY=your_key_here
LIVE_TRANSCRIPTION_PATH=live_transcription.json

# 2. Start server
uvicorn app.main:app --reload

# 3. Test it
curl -X POST http://localhost:8000/workflow/debug/tts --output test.raw

# 4. Check output
cat live_transcription.json
```

## 📄 JSON Format

```json
{
  "transcription": [
    {"word": "hello", "start_time": 0.5, "end_time": 0.8}
  ],
  "last_updated": "2025-10-26T15:42:33.891234+00:00",
  "word_count": 1
}
```

## 💻 Frontend Code (Minimal)

```javascript
// Poll every 500ms
setInterval(async () => {
  const res = await fetch('/live_transcription.json');
  const data = await res.json();
  console.log(`${data.word_count} words`);
}, 500);
```

## ⚙️ Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `LIVE_TRANSCRIPTION_PATH` | `live_transcription.json` | Output file path |
| `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` | `2.0` | Update frequency (seconds) |
| `DEEPGRAM_SAMPLE_RATE` | `48000` | Audio sample rate |
| `DEEPGRAM_STREAM_ENCODING` | `linear16` | Audio encoding |
| `DEEPGRAM_STT_MODEL` | `nova-3` | STT model |

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| No JSON file | Check `LIVE_TRANSCRIPTION_PATH` is set |
| Empty transcription | Wait 2-3 seconds, check API key |
| High latency | Reduce `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` |
| API errors | Verify `DEEPGRAM_API_KEY` is valid |

## 📚 Documentation

- **Quick Start**: `mockly-backend/app/services/workflow/INTEGRATION_GUIDE.md`
- **Full Docs**: `mockly-backend/app/services/workflow/TRANSCRIPTION_README.md`
- **Summary**: `TRANSCRIPTION_SYSTEM_SUMMARY.md`
- **Frontend Demo**: `mockly-backend/app/services/workflow/frontend_example.html`
- **Tests**: `mockly-backend/app/services/workflow/test_live_transcription.py`

## 🎯 Endpoints (Auto-Integrated)

- `POST /workflow/type/stream` - TTS with Claude
- `POST /workflow/input/stream` - Text/voice input
- `GET /workflow/debug/tts` - Debug TTS

## 📊 Performance Tuning

### Fast (Real-time captions)
```bash
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=1.0
```

### Balanced (Recommended)
```bash
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0
```

### Slow (Cost-effective)
```bash
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=4.0
```

## 🐛 Check Logs

```bash
# See transcription activity
grep -i "LiveTranscription" logs/*.log

# See API calls
grep -i "Deepgram" logs/*.log
```

## 💰 Cost Estimate

**1-hour interview** (2s updates):
- TTS: ~$0.45
- STT: ~$0.26
- **Total**: ~$0.71

## ✅ Quick Test

```bash
# Terminal 1: Start server
uvicorn app.main:app --reload

# Terminal 2: Test endpoint
curl -X POST http://localhost:8000/workflow/debug/tts --output test.raw

# Terminal 3: Watch updates
watch -n 0.5 cat live_transcription.json
```

## 🎨 Frontend Example (React)

```jsx
function Captions() {
  const [words, setWords] = useState([]);
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const res = await fetch('/live_transcription.json');
      const data = await res.json();
      setWords(data.transcription);
    }, 500);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div>
      {words.map((w, i) => (
        <span key={i}>{w.word} </span>
      ))}
    </div>
  );
}
```

## 🚨 Emergency Disable

```bash
# Disable live transcription
LIVE_TRANSCRIPTION_PATH=

# Or remove from .env
sed -i '/LIVE_TRANSCRIPTION_PATH/d' .env
```

---

**Need more help?** Read `INTEGRATION_GUIDE.md` for detailed instructions.

