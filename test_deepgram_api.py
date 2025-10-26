#!/usr/bin/env python3
"""
Test script to verify Deepgram API request format.
This will help debug the 400 error by showing exactly what's being sent.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "mockly-backend"
sys.path.insert(0, str(backend_path))

async def test_deepgram_format():
    """Test that we're sending the correct format to Deepgram"""
    
    print("🔍 Testing Deepgram API Request Format")
    print("=" * 60)
    print()
    
    try:
        import httpx
        from app.services.workflow.config import DEEPGRAM_API_KEY, DEEPGRAM_STT_MODEL
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're in the project root and dependencies are installed")
        return False
    
    # Check API key
    if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "your_deepgram_api_key_here":
        print("❌ DEEPGRAM_API_KEY not configured!")
        print("   Set it in your .env file")
        return False
    
    print(f"✅ API Key configured (length: {len(DEEPGRAM_API_KEY)})")
    print(f"✅ Using model: {DEEPGRAM_STT_MODEL}")
    print()
    
    # Create test audio (1 second of silence at 48kHz, 16-bit PCM)
    sample_rate = 48000
    duration_seconds = 1
    bytes_per_sample = 2  # 16-bit = 2 bytes
    channels = 1
    
    test_audio_size = sample_rate * duration_seconds * bytes_per_sample * channels
    test_audio = b'\x00' * test_audio_size  # Silence
    
    print(f"📊 Test audio: {len(test_audio)} bytes ({duration_seconds}s at {sample_rate}Hz)")
    print()
    
    # Prepare request (matching live_transcription.py)
    url = "https://api.deepgram.com/v1/listen"
    
    # Use string values for all params (this is the fix!)
    params = {
        "model": DEEPGRAM_STT_MODEL,
        "punctuate": "true",      # String, not boolean
        "utterances": "false",
        "smart_format": "true",
        "encoding": "linear16",
        "sample_rate": str(sample_rate),  # String
        "channels": "1",
    }
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/raw",
    }
    
    print("📤 Request configuration:")
    print(f"   URL: {url}")
    print(f"   Params: {params}")
    print(f"   Content-Type: {headers['Content-Type']}")
    print()
    
    # Test the request
    print("🔄 Sending test request to Deepgram...")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                content=test_audio,
            )
            
            # Log the actual URL that was called
            print(f"   Actual URL: {response.request.url}")
            print()
            
            if response.status_code == 200:
                print("✅ SUCCESS! Deepgram accepted the request")
                print()
                
                data = response.json()
                transcript = (
                    data.get("results", {})
                    .get("channels", [{}])[0]
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
                
                if transcript:
                    print(f"   Transcript: \"{transcript}\"")
                else:
                    print("   (No speech detected in silent audio - this is expected)")
                
                print()
                print("🎉 The API format is correct!")
                print()
                print("The live transcription should now work when real audio is generated.")
                return True
                
            elif response.status_code == 400:
                print(f"❌ Got 400 Bad Request")
                print()
                print("Response:")
                print(response.text[:500])
                print()
                print("This means the format is still wrong. Common causes:")
                print("- API key invalid")
                print("- Parameters not properly formatted")
                print("- Audio data corrupted")
                return False
                
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
    except httpx.HTTPStatusError as exc:
        print(f"❌ HTTP Error {exc.response.status_code}")
        print(f"   {exc.response.text[:500]}")
        return False
    except Exception as exc:
        print(f"❌ Error: {exc}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print()
    success = await test_deepgram_format()
    print()
    print("=" * 60)
    
    if success:
        print("✅ Deepgram API format test PASSED")
        print()
        print("Next steps:")
        print("1. Restart your backend")
        print("2. Generate TTS audio (ask a question)")
        print("3. Check logs for successful transcription")
        print("4. Verify live_transcription.json has word timestamps")
    else:
        print("❌ Test failed - check the error above")
        print()
        print("If you're still getting 400 errors:")
        print("1. Verify your DEEPGRAM_API_KEY is valid")
        print("2. Check that you're using a Deepgram API key (not project ID)")
        print("3. Ensure your Deepgram account has STT enabled")
        print("4. Try the Deepgram API console to test your key")
    
    print()

if __name__ == "__main__":
    asyncio.run(main())

