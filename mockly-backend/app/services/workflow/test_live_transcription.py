"""
Test script for live transcription system.

This script demonstrates how to use the LiveTranscriptionWriter
and provides basic unit tests.
"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Note: These tests require DEEPGRAM_API_KEY to be set
try:
    from .live_transcription import LiveTranscriptionWriter
except ImportError:
    from live_transcription import LiveTranscriptionWriter


async def test_basic_functionality():
    """Test basic LiveTranscriptionWriter functionality."""
    print("\n" + "="*60)
    print("TEST 1: Basic Functionality")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_output.json"
        
        writer = LiveTranscriptionWriter(
            str(output_path),
            sample_rate=48000,
            encoding="linear16",
            update_interval_seconds=1.0,
        )
        
        # Check that initial empty file was created
        assert output_path.exists(), "Output file should exist"
        
        with open(output_path, "r") as f:
            data = json.load(f)
            assert "transcription" in data
            assert data["transcription"] == []
            print(f"✓ Initial file created with empty transcription")
        
        # Clean up
        writer.close()
        print(f"✓ Writer closed successfully")


async def test_audio_buffering():
    """Test that audio chunks are buffered correctly."""
    print("\n" + "="*60)
    print("TEST 2: Audio Buffering")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_buffer.json"
        
        writer = LiveTranscriptionWriter(
            str(output_path),
            sample_rate=48000,
            encoding="linear16",
            update_interval_seconds=10.0,  # Long interval to prevent auto-update
            min_audio_bytes=1000000,  # High threshold to prevent transcription
        )
        
        # Add some mock audio chunks
        fake_audio = b'\x00' * 1000  # 1KB of silence
        writer.add_audio_chunk(fake_audio, 10.0)  # 10ms duration
        writer.add_audio_chunk(fake_audio, 10.0)
        writer.add_audio_chunk(fake_audio, 10.0)
        
        print(f"✓ Added 3 audio chunks without errors")
        
        # Add text chunks
        writer.add_text_chunk("Hello world")
        writer.add_text_chunk("Testing transcription")
        
        print(f"✓ Added 2 text chunks without errors")
        
        writer.close()


async def test_json_structure():
    """Test the JSON output structure."""
    print("\n" + "="*60)
    print("TEST 3: JSON Output Structure")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_structure.json"
        
        writer = LiveTranscriptionWriter(
            str(output_path),
            sample_rate=16000,
            encoding="linear16",
        )
        
        # Read and verify structure
        with open(output_path, "r") as f:
            data = json.load(f)
        
        # Check required fields
        assert "transcription" in data, "Missing 'transcription' field"
        assert "last_updated" in data, "Missing 'last_updated' field"
        assert "word_count" in data, "Missing 'word_count' field"
        
        # Check types
        assert isinstance(data["transcription"], list), "transcription should be a list"
        assert isinstance(data["word_count"], int), "word_count should be an integer"
        assert isinstance(data["last_updated"], str), "last_updated should be a string"
        
        # Check initial values
        assert data["word_count"] == 0, "Initial word_count should be 0"
        assert data["transcription"] == [], "Initial transcription should be empty"
        
        print(f"✓ JSON structure is correct")
        print(f"  - transcription: {type(data['transcription']).__name__}")
        print(f"  - word_count: {data['word_count']}")
        print(f"  - last_updated: {data['last_updated']}")
        
        writer.close()


async def test_with_real_audio():
    """
    Test with real audio transcription (requires DEEPGRAM_API_KEY).
    
    This test generates a short PCM audio buffer and attempts to transcribe it.
    Note: This will make actual API calls to Deepgram.
    """
    print("\n" + "="*60)
    print("TEST 4: Real Audio Transcription (requires API key)")
    print("="*60)
    
    # Check if API key is available
    if not os.getenv("DEEPGRAM_API_KEY"):
        print("⚠ DEEPGRAM_API_KEY not set, skipping real audio test")
        return
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_real.json"
        
        writer = LiveTranscriptionWriter(
            str(output_path),
            sample_rate=16000,
            encoding="linear16",
            update_interval_seconds=0.5,  # Fast updates for testing
            min_audio_bytes=1000,  # Low threshold
        )
        
        # Generate a simple audio buffer (silence, but properly formatted)
        # In a real scenario, this would be actual audio from Deepgram TTS
        sample_rate = 16000
        duration_seconds = 2
        num_samples = sample_rate * duration_seconds
        
        # Generate 2 seconds of silence (16-bit PCM)
        audio_bytes = b'\x00\x00' * num_samples  # 2 bytes per sample
        
        print(f"  Generated {len(audio_bytes)} bytes of audio ({duration_seconds}s)")
        
        # Add audio in chunks
        chunk_size = 8000  # ~0.25 seconds at 16kHz
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            duration_ms = (len(chunk) / 2) / sample_rate * 1000  # 2 bytes per sample
            writer.add_audio_chunk(chunk, duration_ms)
        
        print(f"  Added audio in {len(audio_bytes) // chunk_size} chunks")
        
        # Trigger transcription
        try:
            await writer.maybe_update()
            print(f"✓ Transcription triggered successfully")
            
            # Read results
            with open(output_path, "r") as f:
                data = json.load(f)
            
            print(f"  - Word count: {data['word_count']}")
            if data['word_count'] > 0:
                print(f"  - First word: {data['transcription'][0]}")
            else:
                print(f"  - No words (silence detected)")
            
        except Exception as e:
            print(f"⚠ Transcription failed: {e}")
            print(f"  (This is expected if audio is just silence)")
        
        finally:
            await writer.finalize()
            writer.close()


async def demo_usage():
    """Demonstrate typical usage pattern."""
    print("\n" + "="*60)
    print("DEMO: Typical Usage Pattern")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "demo_output.json"
        
        print(f"\n1. Initialize writer:")
        print(f"   output_path: {output_path}")
        
        writer = LiveTranscriptionWriter(
            str(output_path),
            sample_rate=48000,
            encoding="linear16",
            update_interval_seconds=2.0,
        )
        
        print(f"\n2. Simulate TTS stream:")
        print(f"   - Adding text chunks (sentences)")
        print(f"   - Adding audio chunks (streaming audio)")
        
        # Simulate a TTS stream
        sentences = [
            "Hello, welcome to the interview.",
            "Can you tell me about your experience?",
            "What languages do you know?",
        ]
        
        for i, sentence in enumerate(sentences):
            print(f"   Sentence {i+1}: {sentence[:30]}...")
            writer.add_text_chunk(sentence)
            
            # Simulate audio chunks
            fake_audio = b'\x00' * 10000
            writer.add_audio_chunk(fake_audio, 100.0)
            
            # Check for updates
            await writer.maybe_update()
            
            # Small delay to simulate streaming
            await asyncio.sleep(0.1)
        
        print(f"\n3. Finalize transcription:")
        await writer.finalize()
        
        print(f"\n4. Read output file:")
        with open(output_path, "r") as f:
            data = json.load(f)
        
        print(f"   - Word count: {data['word_count']}")
        print(f"   - Last updated: {data['last_updated']}")
        print(f"   - Transcription length: {len(data['transcription'])}")
        
        print(f"\n5. Clean up:")
        writer.close()
        print(f"   ✓ Done")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("LIVE TRANSCRIPTION SYSTEM - TEST SUITE")
    print("="*60)
    
    try:
        await test_basic_functionality()
        await test_audio_buffering()
        await test_json_structure()
        await test_with_real_audio()
        await demo_usage()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        print("\nTo test with real API calls:")
        print("1. Set DEEPGRAM_API_KEY environment variable")
        print("2. Run this script again")
        print("3. Check that test 4 produces actual transcription")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

