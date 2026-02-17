"""
Manual test for Audio Transcription (Gemini & Whisper).
Downloads a sample audio and tests transcription service.
"""
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Add local libs (priority)
libs_path = os.path.join(os.getcwd(), "libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from src.core.audio_service import audio_service, TranscriptionBackend
from src.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_audio_transcription():
    print("--- Starting Audio Transcription Test ---")
    
    import httpx
    
    # 1. Download Sample Audio (Wikipedia spoken article snippet)
    # A short clip is better.
    url = "https://upload.wikimedia.org/wikipedia/commons/d/dd/Armstrong_Small_Step.ogg" # Neil Armstrong
    print(f"Downloading Audio from {url}...")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            print(f"❌ Failed to download Audio: {resp.status_code}")
            return
        audio_bytes = resp.content
        print(f"Downloaded {len(audio_bytes)} bytes.")

    # 2. Test Gemini
    print("\n--- Testing Gemini Backend ---")
    try:
        text = await audio_service.transcribe(audio_bytes, "audio/ogg", backend=TranscriptionBackend.GEMINI)
        print(f"✅ Gemini Transcription: {text.strip()[:100]}...")
    except Exception as e:
        print(f"❌ Gemini Failed: {e}")

    # 3. Test Whisper (if API key present)
    if settings.OPENAI_API_KEY or settings.GROQ_API_KEY:
        print("\n--- Testing Whisper Backend ---")
        try:
            text = await audio_service.transcribe(audio_bytes, "audio/ogg", backend=TranscriptionBackend.WHISPER)
            print(f"✅ Whisper Transcription: {text.strip()[:100]}...")
        except Exception as e:
            print(f"❌ Whisper Failed: {e}")
    else:
        print("\n⚠️ Skipping Whisper (No API KEY)")

if __name__ == "__main__":
    asyncio.run(test_audio_transcription())
