# Live Timestamped Transcription System

## Overview

This system provides real-time word-level timestamps for TTS-generated audio, creating a continuously updated JSON file that the frontend can poll for synchronized captions and subtitles.

## How It Works

```
┌─────────────────┐
│  Claude Text    │
│   Generation    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Deepgram TTS   │
│  (Text → Audio) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Audio Buffer   │─────▶│  Deepgram STT    │
│  (PCM 16-bit)   │      │  (Audio → Text)  │
└─────────────────┘      │  with timestamps │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  JSON File       │
                         │  (Overwrite)     │
                         │  - word          │
                         │  - start_time    │
                         │  - end_time      │
                         └──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Frontend Polls  │
                         │  for Updates     │
                         └──────────────────┘
```

### Process Flow

1. **TTS Generation**: Claude generates text, which is sent to Deepgram TTS
2. **Audio Streaming**: Audio chunks are streamed back from Deepgram
3. **Buffer Accumulation**: Audio chunks are accumulated in a buffer
4. **Periodic Transcription**: Every `N` seconds (configurable), the buffer is:
   - Sent to Deepgram STT for transcription with word-level timestamps
   - Buffer is cleared after successful transcription
5. **JSON Update**: The transcription results are written to JSON file (full overwrite)
6. **Frontend Polling**: The frontend polls the JSON file for updates

## Configuration

Add these environment variables to your `.env` file:

```bash
# Enable live transcription (set to file path)
LIVE_TRANSCRIPTION_PATH=live_transcription.json

# Update frequency in seconds (default: 2.0)
# Lower values = more frequent updates, higher API usage
# Higher values = less frequent updates, longer delay
LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0

# Deepgram API credentials (required)
DEEPGRAM_API_KEY=your_api_key_here

# Audio configuration (defaults shown)
DEEPGRAM_SAMPLE_RATE=48000
DEEPGRAM_STREAM_ENCODING=linear16
DEEPGRAM_STT_MODEL=nova-3
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LIVE_TRANSCRIPTION_PATH` | `live_transcription.json` | Output file path for transcription JSON |
| `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` | `2.0` | Seconds between JSON updates |
| `DEEPGRAM_SAMPLE_RATE` | `48000` | Audio sample rate in Hz |
| `DEEPGRAM_STREAM_ENCODING` | `linear16` | Audio encoding format (PCM 16-bit) |
| `DEEPGRAM_STT_MODEL` | `nova-3` | Deepgram STT model to use |

## JSON Output Format

### Structure

```json
{
  "transcription": [
    {
      "word": "hello",
      "start_time": 0.5,
      "end_time": 0.8
    },
    {
      "word": "world",
      "start_time": 0.9,
      "end_time": 1.2
    }
  ],
  "last_updated": "2025-10-26T10:30:45.123456+00:00",
  "word_count": 2
}
```

### Field Descriptions

- **transcription**: Array of word objects with timestamps
  - **word**: The transcribed word (string)
  - **start_time**: Start time in seconds from beginning of audio (float)
  - **end_time**: End time in seconds from beginning of audio (float)
- **last_updated**: ISO 8601 timestamp of when the file was last updated (UTC)
- **word_count**: Total number of words transcribed so far (integer)

### Example Output

```json
{
  "transcription": [
    {
      "word": "let's",
      "start_time": 0.0,
      "end_time": 0.28
    },
    {
      "word": "start",
      "start_time": 0.28,
      "end_time": 0.56
    },
    {
      "word": "with",
      "start_time": 0.56,
      "end_time": 0.72
    },
    {
      "word": "the",
      "start_time": 0.72,
      "end_time": 0.84
    },
    {
      "word": "interview",
      "start_time": 0.84,
      "end_time": 1.4
    }
  ],
  "last_updated": "2025-10-26T15:42:33.891234+00:00",
  "word_count": 5
}
```

## Integration Points

### Backend Integration

The system automatically integrates with existing TTS endpoints when configured:

- `/type/stream` - Streaming TTS with Claude text generation
- `/input/stream` - Streaming with text or voice input
- `/debug/tts` - Debug TTS endpoint

**No code changes needed** - just set the environment variables.

### Frontend Integration

The frontend should:

1. **Poll the JSON file** at regular intervals (e.g., every 500ms)
2. **Parse the transcription array** to get word timestamps
3. **Sync with audio playback** using start_time/end_time
4. **Display captions** or highlight current word

#### Example Frontend Code (JavaScript)

```javascript
class LiveTranscriptionReader {
  constructor(jsonPath, pollInterval = 500) {
    this.jsonPath = jsonPath;
    this.pollInterval = pollInterval;
    this.lastUpdate = null;
    this.words = [];
  }

  async start() {
    this.intervalId = setInterval(() => this.poll(), this.pollInterval);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  async poll() {
    try {
      const response = await fetch(this.jsonPath);
      const data = await response.json();
      
      // Only process if file was updated
      if (data.last_updated !== this.lastUpdate) {
        this.lastUpdate = data.last_updated;
        this.words = data.transcription;
        this.onUpdate(data);
      }
    } catch (error) {
      console.error('Failed to fetch transcription:', error);
    }
  }

  onUpdate(data) {
    // Override this method to handle updates
    console.log(`Received ${data.word_count} words`);
  }

  getCurrentWord(currentTime) {
    return this.words.find(
      w => currentTime >= w.start_time && currentTime < w.end_time
    );
  }

  getWordsUpTo(currentTime) {
    return this.words.filter(w => w.start_time <= currentTime);
  }
}

// Usage
const reader = new LiveTranscriptionReader('/live_transcription.json');
reader.onUpdate = (data) => {
  console.log('Transcription updated:', data.word_count, 'words');
  updateCaptions(data.transcription);
};
reader.start();
```

## Performance Considerations

### Update Frequency

The `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` setting affects:

- **API Usage**: More frequent updates = more API calls to Deepgram STT
- **Latency**: Less frequent updates = longer delay before words appear
- **CPU/IO**: More frequent updates = more file writes and processing

**Recommended values**:
- **High responsiveness**: 1.5 - 2.0 seconds
- **Balanced**: 2.0 - 3.0 seconds
- **Conservative**: 3.0 - 5.0 seconds

### API Costs

Each update triggers a Deepgram STT API call. Estimated costs:

- **Update every 2 seconds** on a 60-second audio stream = ~30 API calls
- With audio buffering, actual calls are fewer (only when buffer has sufficient data)

### File Operations

The system uses **atomic file replacement** to prevent partial reads:

1. Write to temporary file (`live_transcription.tmp`)
2. Atomic rename/replace of target file
3. Frontend always sees complete, valid JSON

## Error Handling

### Common Issues

1. **No words appearing in JSON**
   - Check that `DEEPGRAM_API_KEY` is valid
   - Verify audio is being generated (check logs)
   - Ensure `LIVE_TRANSCRIPTION_PATH` is set

2. **Transcription lag too high**
   - Reduce `LIVE_TRANSCRIPTION_UPDATE_INTERVAL`
   - Check network latency to Deepgram API
   - Verify sufficient CPU resources

3. **File access errors**
   - Ensure output directory exists and is writable
   - Check file permissions
   - Verify no other process is locking the file

### Logging

The system logs key events:

```
[LiveTranscription] Initialized: output=live_transcription.json, sample_rate=48000, update_interval=2.0s
[LiveTranscription] Updated with 15 new words (total: 47)
[LiveTranscription] Finalized with 52 total words
```

Check logs if transcription isn't working as expected.

## Advanced Usage

### Custom Output Path

You can set a custom path (absolute or relative):

```bash
# Relative to backend directory
LIVE_TRANSCRIPTION_PATH=output/captions/live.json

# Absolute path
LIVE_TRANSCRIPTION_PATH=/var/www/static/live_transcription.json
```

### Disabling Live Transcription

To disable, simply don't set `LIVE_TRANSCRIPTION_PATH` or set it to empty:

```bash
LIVE_TRANSCRIPTION_PATH=
```

### Combining with Captions

You can use both systems simultaneously:

```bash
# Event-based logging (appends to file)
TTS_LIVE_JSON_PATH=tts_events.ndjson

# Word-level transcription (overwrites file)
LIVE_TRANSCRIPTION_PATH=live_transcription.json
```

## Technical Details

### Audio Format

The system expects **PCM 16-bit mono audio** from Deepgram TTS:
- **Sample Rate**: 48000 Hz (configurable)
- **Encoding**: Linear16 (signed 16-bit PCM)
- **Channels**: 1 (mono)

### Thread Safety

- Uses `threading.Lock` for thread-safe buffer access
- Atomic file writes prevent partial reads
- Safe for concurrent audio streaming

### Memory Management

- Audio buffer is cleared after each transcription
- Only accumulates ~1-3 seconds of audio at a time
- Low memory footprint (~200KB per active stream)

## Testing

### Manual Test

1. Set environment variables:
   ```bash
   export LIVE_TRANSCRIPTION_PATH=test_output.json
   export LIVE_TRANSCRIPTION_UPDATE_INTERVAL=2.0
   ```

2. Start the backend server

3. Call a TTS endpoint:
   ```bash
   curl -X POST http://localhost:8000/workflow/type/stream \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, this is a test of the live transcription system."}' \
     --output audio.raw
   ```

4. Monitor the JSON file:
   ```bash
   watch -n 0.5 cat test_output.json
   ```

### Automated Testing

See `test_live_transcription.py` for unit tests and integration tests.

## Troubleshooting

### Problem: No JSON file created

**Solution**: Check that `LIVE_TRANSCRIPTION_PATH` is set and the directory is writable.

```bash
# Verify directory exists
mkdir -p $(dirname $LIVE_TRANSCRIPTION_PATH)

# Check permissions
ls -la $LIVE_TRANSCRIPTION_PATH
```

### Problem: Empty transcription array

**Causes**:
1. Not enough audio buffered yet (wait for update interval)
2. Deepgram STT API error (check logs)
3. Audio format mismatch (verify encoding is linear16)

**Solution**: Check logs for error messages:
```bash
grep -i "LiveTranscription\|Deepgram" logs/backend.log
```

### Problem: Timestamps don't match audio

**Causes**:
1. Sample rate mismatch
2. Audio buffering delays
3. Network latency

**Solution**: 
- Verify `DEEPGRAM_SAMPLE_RATE` matches actual audio sample rate
- Reduce `LIVE_TRANSCRIPTION_UPDATE_INTERVAL` for better accuracy
- Consider using absolute timestamps from audio player instead of file timestamps

## Architecture

### Class: LiveTranscriptionWriter

**Purpose**: Manages audio buffering, transcription requests, and JSON file updates.

**Key Methods**:
- `add_audio_chunk(bytes, duration_ms)`: Add audio to buffer
- `add_text_chunk(text)`: Track text sent to TTS (optional)
- `maybe_update()`: Check and trigger update if needed
- `finalize()`: Process remaining audio at end of stream
- `close()`: Clean up resources

**State**:
- Audio buffer (in-memory BytesIO)
- Accumulated word list
- Last update timestamp
- Configuration parameters

### Integration with TTS Pipeline

The system hooks into two TTS streaming functions:

1. **stream_deepgram_tts**: Uses Deepgram SDK client
2. **stream_deepgram_tts_raw**: Uses websockets directly

Both functions:
- Initialize `LiveTranscriptionWriter` if configured
- Call `add_audio_chunk()` for each audio frame
- Call `maybe_update()` to trigger periodic updates
- Call `finalize()` when stream completes

## Future Enhancements

Potential improvements for future versions:

1. **Caching**: Cache transcription results to avoid re-processing
2. **Incremental Updates**: Only transcribe new audio segments
3. **WebSocket Support**: Push updates to frontend instead of polling
4. **Format Options**: Support other output formats (SRT, VTT, etc.)
5. **Confidence Scores**: Include Deepgram confidence scores in output
6. **Speaker Diarization**: Support multi-speaker scenarios

## Support

For issues or questions:
1. Check logs for error messages
2. Verify environment variables are set correctly
3. Test with minimal example first
4. Review this documentation for configuration options

## License

This code is part of the Mockly backend system.

