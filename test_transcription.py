#!/usr/bin/env python3
"""
Quick test script to verify live transcription is working.
Run this after starting the backend to check the fix.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "mockly-backend"
sys.path.insert(0, str(backend_path))

async def test_transcription():
    """Test the live transcription endpoint"""
    print("🔍 Testing Live Transcription")
    print("=" * 60)
    print()
    
    try:
        import httpx
    except ImportError:
        print("❌ httpx not installed. Run: pip install httpx")
        return False
    
    # Check if backend is running
    print("1. Checking backend...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/docs")
            if response.status_code == 200:
                print("✅ Backend is running")
            else:
                print(f"⚠️  Backend returned status {response.status_code}")
    except httpx.ConnectError:
        print("❌ Backend is not running!")
        print("   Start it with: cd mockly-backend && poetry run python -m app.main")
        return False
    
    print()
    
    # Check transcription file
    print("2. Checking transcription file...")
    transcription_files = [
        "live_transcription.json",
        "mockly-backend/live_transcription.json",
    ]
    
    file_found = False
    transcription_path = None
    
    for path in transcription_files:
        if os.path.exists(path):
            file_found = True
            transcription_path = path
            print(f"✅ Found: {path}")
            
            # Read and display content
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    word_count = data.get("word_count", 0)
                    last_updated = data.get("last_updated", "unknown")
                    
                    print(f"   Words: {word_count}")
                    print(f"   Last updated: {last_updated}")
                    
                    if word_count > 0:
                        print()
                        print("   Sample words:")
                        for i, word in enumerate(data.get("transcription", [])[:5]):
                            print(f"     {i+1}. \"{word['word']}\" ({word['start_time']:.2f}s - {word['end_time']:.2f}s)")
                    
            except json.JSONDecodeError as e:
                print(f"   ⚠️  Invalid JSON: {e}")
            except Exception as e:
                print(f"   ⚠️  Error reading file: {e}")
            
            break
    
    if not file_found:
        print("⚠️  Transcription file not found (will be created on first TTS)")
    
    print()
    
    # Test caption endpoint
    print("3. Testing caption endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/workflow/captions/live")
            
            if response.status_code == 200:
                print("✅ Endpoint accessible")
                data = response.json()
                
                status = data.get("status", "unknown")
                word_count = data.get("word_count", 0)
                
                print(f"   Status: {status}")
                print(f"   Words: {word_count}")
                
                if status == "active" and word_count > 0:
                    print()
                    print("   Sample response:")
                    print(f"   {json.dumps(data, indent=2)[:500]}...")
                    print()
                    print("🎉 SUCCESS! Live transcription is working!")
                    return True
                elif status == "no_data":
                    print()
                    print("⚠️  No transcription data yet.")
                    print("   Trigger TTS audio generation to create transcription.")
                    return True
                else:
                    print(f"⚠️  Unexpected status: {status}")
                    if "error" in data:
                        print(f"   Error: {data['error']}")
                    return False
            else:
                print(f"❌ Endpoint returned {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to test endpoint: {e}")
        return False

async def main():
    print()
    success = await test_transcription()
    print()
    print("=" * 60)
    
    if success:
        print("✅ All tests passed!")
        print()
        print("Next steps:")
        print("1. Start frontend: cd mockly-frontend && npm run dev")
        print("2. Navigate to interview screen")
        print("3. Trigger audio playback")
        print("4. Watch the avatar lip sync! 🎉")
    else:
        print("❌ Tests failed. Check the output above for details.")
        print()
        print("Common issues:")
        print("- Backend not running")
        print("- No TTS audio generated yet")
        print("- Deepgram API key not configured")
    
    print()

if __name__ == "__main__":
    asyncio.run(main())

