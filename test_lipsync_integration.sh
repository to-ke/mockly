#!/bin/bash

echo "🔍 Testing Lip Sync Integration"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
echo "1. Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not running${NC}"
    echo "  Please start: cd mockly-backend && poetry run python -m app.main"
    exit 1
fi

echo ""
echo "2. Checking live transcription configuration..."

# Check if transcription file exists (might not exist until first TTS)
if [ -f "mockly-backend/live_transcription.json" ] || [ -f "live_transcription.json" ]; then
    echo -e "${GREEN}✓ Live transcription file exists${NC}"
    
    # Show file contents
    echo ""
    echo "   Current transcription data:"
    if [ -f "mockly-backend/live_transcription.json" ]; then
        cat mockly-backend/live_transcription.json | python3 -m json.tool 2>/dev/null || cat mockly-backend/live_transcription.json
    else
        cat live_transcription.json | python3 -m json.tool 2>/dev/null || cat live_transcription.json
    fi
else
    echo -e "${YELLOW}⚠ Live transcription file not found (will be created on first TTS)${NC}"
fi

echo ""
echo "3. Testing captions endpoint..."
response=$(curl -s http://localhost:8000/api/workflow/captions/live)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Captions endpoint is accessible${NC}"
    echo ""
    echo "   Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    
    # Check status
    status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null)
    word_count=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('word_count', 0))" 2>/dev/null)
    
    if [ "$status" = "active" ] && [ "$word_count" -gt 0 ]; then
        echo -e "${GREEN}✓ Captions are active with $word_count words${NC}"
    elif [ "$status" = "no_data" ]; then
        echo -e "${YELLOW}⚠ No transcription data yet (trigger TTS first)${NC}"
    else
        echo -e "${YELLOW}⚠ Status: $status${NC}"
    fi
else
    echo -e "${RED}✗ Failed to access captions endpoint${NC}"
    exit 1
fi

echo ""
echo "4. Checking frontend setup..."

if [ -f "mockly-frontend/src/components/TalkingHeadSync.tsx" ]; then
    echo -e "${GREEN}✓ TalkingHeadSync component exists${NC}"
else
    echo -e "${RED}✗ TalkingHeadSync component not found${NC}"
    exit 1
fi

if [ -f "mockly-frontend/src/lib/lipsyncController.ts" ]; then
    echo -e "${GREEN}✓ LipsyncController utility exists${NC}"
else
    echo -e "${RED}✗ LipsyncController utility not found${NC}"
    exit 1
fi

echo ""
echo "================================"
echo "✅ Integration test complete!"
echo ""
echo "Next steps:"
echo "1. Start frontend: cd mockly-frontend && npm run dev"
echo "2. Navigate to your interview screen"
echo "3. Trigger audio playback"
echo "4. Watch the avatar lip sync! 🎉"
echo ""
echo "If no lip movement:"
echo "- Check browser console for errors"
echo "- Verify audio is playing"
echo "- Check that captions endpoint returns words"
echo ""
echo "For more details, see: LIPSYNC_FIX_SUMMARY.md"

