# Live Transcription - Quick Integration Guide

## Quick Start (5 minutes)

### 1. Configure Environment Variables

Add to your `.env` file:

```bash
# Required: Your Deepgram API key
DEEPGRAM_API_KEY=your_key_here

# Enable live transcription
LIVE_TRANSCRIPTION_PATH=live_transcription.json

# Optional: Adjust update frequency (default: 2.0 seconds)
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0
```

### 2. Start Your Backend Server

```bash
cd mockly-backend
python -m uvicorn app.main:app --reload
```

### 3. Test the System

Send a request to any TTS endpoint:

```bash
curl -X POST http://localhost:8000/workflow/type/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test of live transcription."}' \
  --output audio.raw
```

### 4. Monitor the Output

While the audio is streaming, watch the JSON file update:

```bash
# Linux/Mac
watch -n 0.5 cat live_transcription.json

# Windows PowerShell
while($true) { Clear-Host; Get-Content live_transcription.json; Start-Sleep -Seconds 0.5 }
```

You should see something like:

```json
{
  "transcription": [
    {"word": "hello", "start_time": 0.0, "end_time": 0.28},
    {"word": "this", "start_time": 0.32, "end_time": 0.48}
  ],
  "last_updated": "2025-10-26T15:42:33.891234+00:00",
  "word_count": 2
}
```

## Integration with Existing Endpoints

The system **automatically integrates** with these endpoints when `LIVE_TRANSCRIPTION_PATH` is configured:

### `/workflow/type/stream`

Streams TTS audio with Claude text generation.

**Request:**
```bash
curl -X POST http://localhost:8000/workflow/type/stream \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Explain what a linked list is",
    "difficulty": "medium"
  }' \
  --output response.raw
```

**Result:** 
- Audio streams to the client
- `live_transcription.json` updates every N seconds with word timestamps

### `/workflow/input/stream`

Handles both text and voice input with TTS response.

**Request:**
```bash
curl -X POST http://localhost:8000/workflow/input/stream \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "text",
    "text": "What is recursion?",
    "difficulty": "easy"
  }' \
  --output response.raw
```

**Result:**
- Audio streams to the client
- Live transcription file updates automatically

### `/workflow/debug/tts`

Debug endpoint for testing TTS without Claude.

**Request:**
```bash
curl http://localhost:8000/workflow/debug/tts \
  --output test.raw
```

**Result:**
- Plays test audio
- Updates transcription file with test sentences

## Frontend Integration

### Option 1: Simple Polling (Recommended)

```javascript
// Poll the JSON file every 500ms
async function pollTranscription() {
  try {
    const response = await fetch('/live_transcription.json');
    const data = await response.json();
    displayTranscription(data.transcription);
  } catch (error) {
    console.error('Failed to fetch transcription:', error);
  }
}

// Start polling
setInterval(pollTranscription, 500);
```

### Option 2: Class-Based Approach

```javascript
class TranscriptionClient {
  constructor(jsonPath = '/live_transcription.json') {
    this.jsonPath = jsonPath;
    this.lastUpdate = null;
  }

  async start(callback, interval = 500) {
    this.callback = callback;
    this.intervalId = setInterval(() => this.fetch(), interval);
    await this.fetch(); // Immediate first fetch
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  async fetch() {
    try {
      const response = await fetch(this.jsonPath);
      const data = await response.json();
      
      // Only callback if data changed
      if (data.last_updated !== this.lastUpdate) {
        this.lastUpdate = data.last_updated;
        this.callback(data);
      }
    } catch (error) {
      console.error('Fetch error:', error);
    }
  }
}

// Usage
const client = new TranscriptionClient();
client.start((data) => {
  console.log(`Got ${data.word_count} words`);
  updateCaptions(data.transcription);
});
```

### Option 3: React Hook

```javascript
import { useState, useEffect } from 'react';

function useLiveTranscription(jsonPath = '/live_transcription.json', interval = 500) {
  const [transcription, setTranscription] = useState([]);
  const [wordCount, setWordCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    let lastUpdateStr = null;

    const fetchData = async () => {
      try {
        const response = await fetch(jsonPath);
        const data = await response.json();
        
        if (data.last_updated !== lastUpdateStr) {
          lastUpdateStr = data.last_updated;
          setTranscription(data.transcription);
          setWordCount(data.word_count);
          setLastUpdate(new Date(data.last_updated));
        }
      } catch (error) {
        console.error('Failed to fetch transcription:', error);
      }
    };

    const intervalId = setInterval(fetchData, interval);
    fetchData(); // Immediate fetch

    return () => clearInterval(intervalId);
  }, [jsonPath, interval]);

  return { transcription, wordCount, lastUpdate };
}

// Usage in component
function TranscriptionViewer() {
  const { transcription, wordCount } = useLiveTranscription();

  return (
    <div>
      <h2>Transcription ({wordCount} words)</h2>
      <div>
        {transcription.map((word, i) => (
          <span key={i} title={`${word.start_time}s - ${word.end_time}s`}>
            {word.word}{' '}
          </span>
        ))}
      </div>
    </div>
  );
}
```

## Serving the JSON File

### Development Setup

If your backend and frontend are on the same server:

```python
# In FastAPI (already done if using mockly)
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

Set path to: `LIVE_TRANSCRIPTION_PATH=static/live_transcription.json`

Frontend fetches: `/static/live_transcription.json`

### Production Setup

**Option 1: Nginx Static File Serving**

```nginx
location /live_transcription.json {
    alias /var/www/mockly/live_transcription.json;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Access-Control-Allow-Origin "*";
}
```

**Option 2: Direct Backend Serving**

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse

@app.get("/live_transcription.json")
async def get_live_transcription():
    return FileResponse("live_transcription.json")
```

**Option 3: Cloud Storage**

Upload the JSON file to S3/GCS after each update:

```python
# Add to live_transcription.py after file write
import boto3

def _write_json_file(self, words):
    # ... existing file write code ...
    
    # Upload to S3
    if self.upload_to_s3:
        s3 = boto3.client('s3')
        s3.upload_file(
            str(self.output_path),
            'my-bucket',
            'live_transcription.json'
        )
```

## Testing Checklist

- [ ] Environment variables configured
- [ ] Backend server running
- [ ] Test endpoint returns audio: `curl .../workflow/debug/tts`
- [ ] JSON file created in expected location
- [ ] JSON file updates every N seconds during audio stream
- [ ] JSON structure matches expected format
- [ ] Frontend can fetch and parse JSON
- [ ] Word timestamps are accurate (±0.1s)
- [ ] File updates stop after audio stream ends

## Troubleshooting

### Issue: JSON file not created

**Check:**
1. Is `LIVE_TRANSCRIPTION_PATH` set in `.env`?
2. Does the directory exist and is it writable?
3. Are there errors in the logs?

**Fix:**
```bash
# Create directory if needed
mkdir -p $(dirname $LIVE_TRANSCRIPTION_PATH)

# Check permissions
ls -la $LIVE_TRANSCRIPTION_PATH
```

### Issue: Empty transcription array

**Check:**
1. Is audio actually being generated? (check logs)
2. Is `DEEPGRAM_API_KEY` valid?
3. Have you waited for at least one update interval?

**Fix:**
```bash
# Check logs for errors
grep -i "LiveTranscription\|Deepgram" logs/*.log

# Verify API key
curl -X POST https://api.deepgram.com/v1/listen \
  -H "Authorization: Token $DEEPGRAM_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @test.wav
```

### Issue: Transcription lag too high

**Check:**
1. Current `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` value
2. Network latency to Deepgram API
3. Server CPU usage

**Fix:**
```bash
# Reduce update interval for faster updates
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=1.0

# Or increase for less load
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=3.0
```

### Issue: Frontend can't fetch JSON

**Check:**
1. CORS headers configured?
2. JSON file path correct?
3. File actually exists?

**Fix:**
```python
# Add CORS middleware (should already exist in mockly)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Performance Tips

1. **Adjust update interval** based on your needs:
   - Real-time captions: 1.0-1.5s (higher API cost)
   - Normal use: 2.0-2.5s (balanced)
   - Low traffic: 3.0-5.0s (lower API cost)

2. **Cache frontend requests** with short TTL:
   ```javascript
   // Add cache control
   fetch('/live_transcription.json', {
     cache: 'no-store'  // Ensure fresh data
   })
   ```

3. **Use CDN** for production:
   - Upload JSON to CDN after each update
   - Frontend fetches from CDN (lower latency)

4. **Monitor API usage**:
   - Track Deepgram API calls
   - Adjust interval if costs are too high
   - Consider caching for repeated requests

## Next Steps

1. ✅ Configure environment variables
2. ✅ Test with debug endpoint
3. ✅ Verify JSON file updates
4. ✅ Integrate frontend polling
5. ✅ Test with real interview flow
6. ✅ Deploy to production
7. ✅ Monitor API costs and performance

## Need Help?

- Check logs: `grep -i transcription logs/*.log`
- Review code: `app/services/workflow/live_transcription.py`
- Read docs: `TRANSCRIPTION_README.md`
- Run tests: `python test_live_transcription.py`

## Additional Resources

- **Full Documentation**: `TRANSCRIPTION_README.md`
- **Example Frontend**: `frontend_example.html`
- **Test Script**: `test_live_transcription.py`
- **Example Output**: `example_output.json`
- **Environment Template**: `example.env`

