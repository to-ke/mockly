# 🚀 Quick Start: TalkingHead Lipsync

Get lip sync working in 5 minutes!

## ⚡ Latest Update

**FIXED:** Now using **real Deepgram STT transcription** with precise word timestamps instead of estimated timing. This provides professional-quality lip sync! See `LIPSYNC_FIX_SUMMARY.md` for details.

## Step 1: Verify Backend (Already Done! ✅)

Your backend is already configured with live transcription enabled. Just make sure it's running:

```bash
cd mockly-backend
poetry run python -m app.main
```

## Step 2: Replace Component (2 lines of code)

In your main app component where you use the avatar:

```tsx
// ❌ OLD
import { TalkingHead } from '@/components/TalkingHead'

<TalkingHead 
  modelUrl={modelUrl}
  className="h-96"
/>

// ✅ NEW
import { TalkingHeadSync } from '@/components/TalkingHeadSync'

<TalkingHeadSync
  audioUrl={audioUrl}           // Pass your audio URL
  enableSync={true}              // Enable lip sync
  modelUrl={modelUrl}
  className="h-96"
  onSpeakingStateChange={(speaking) => {
    console.log('Avatar speaking:', speaking)
  }}
/>
```

## Step 3: Test It!

```bash
cd mockly-frontend
npm run dev
```

1. Navigate to your interview/conversation screen
2. Trigger audio playback (e.g., ask a question)
3. Watch the avatar's mouth move in sync! 🎉

## That's It!

The system handles everything automatically:
- Fetches captions from backend
- Syncs mouth with audio
- Shows current word
- Cleans up when done

## Example: Complete Integration

```tsx
import { useState } from 'react'
import { TalkingHeadSync } from '@/components/TalkingHeadSync'
import { useVoice } from '@/stores/voice'

function InterviewScreen() {
  const { audioUrl, setAvatarSpeaking } = useVoice()

  return (
    <div className="container">
      <h1>Mock Interview</h1>
      
      <TalkingHeadSync
        audioUrl={audioUrl}
        enableSync={true}
        onSpeakingStateChange={setAvatarSpeaking}
        className="w-full h-96"
      />
      
      {/* Rest of your UI */}
    </div>
  )
}
```

## Troubleshooting

### No lip movement?

**Check 1:** Is audio playing?
```tsx
<audio src={audioUrl} controls />  // Test audio
```

**Check 2:** Are captions available?
```bash
# Open browser console and run:
fetch('/api/workflow/captions/live')
  .then(r => r.json())
  .then(console.log)

# Should show: {words: [...], status: "active"}
```

**Check 3:** Backend running?
```bash
curl http://localhost:8000/api/workflow/captions/live
```

### Still stuck?

See full documentation: `mockly-frontend/LIPSYNC_INTEGRATION.md`

## What's Next?

- ✅ Basic lip sync working
- 🎯 Adjust polling interval for better responsiveness
- 🎯 Add eye blinking
- 🎯 Add head movements
- 🎯 Customize phoneme mapping

See `LIPSYNC_INTEGRATION.md` for advanced features!

---

**You're all set!** 🎉 Enjoy your synchronized talking avatar!

