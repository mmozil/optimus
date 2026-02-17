"""
Agent Optimus — Audio Service.
Handles audio transcription using multiple backends (Gemini, Whisper).
"""
import logging
import io
import os
from enum import Enum
from typing import Optional

# Conditional imports
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from src.infra.model_router import model_router
from src.core.config import settings

logger = logging.getLogger(__name__)

class TranscriptionBackend(str, Enum):
    GEMINI = "gemini"
    WHISPER = "whisper"

class AudioService:
    """
    Unified interface for audio transcription.
    """
    
    def __init__(self):
        self.openai_client = None
        if AsyncOpenAI and settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # We can also use Groq for Whisper if configured
        if AsyncOpenAI and settings.GROQ_API_KEY and not self.openai_client:
             self.openai_client = AsyncOpenAI(
                 base_url="https://api.groq.com/openai/v1",
                 api_key=settings.GROQ_API_KEY
             )

    async def transcribe(
        self, 
        content: bytes, 
        mime_type: str, 
        backend: TranscriptionBackend = TranscriptionBackend.GEMINI
    ) -> str:
        """
        Transcribe audio content to text.
        """
        if backend == TranscriptionBackend.GEMINI:
            return await self._transcribe_gemini(content, mime_type)
        elif backend == TranscriptionBackend.WHISPER:
            return await self._transcribe_whisper(content, mime_type)
        else:
            raise ValueError(f"Unknown backend: {backend}")

    async def _transcribe_gemini(self, content: bytes, mime_type: str) -> str:
        """
        Use Gemini Flash Multimodal for transcription.
        Sending audio as a part of the prompt.
        """
        logger.info("Transcribing audio with Gemini...")
        
        # We construct a multimodal message manually for ModelRouter
        # ModelRouter expects structured messages.
        # But wait, ModelRouter._native_gemini_call needs to support 'audio' type parts first.
        # Or we can use the 'image_url' logic if we extend it, but audio needs blob data usually.
        # Ideally, we upload the file to Gemini File API if it's large, 
        # or pass inline data if small (< 20MB).
        
        # For simplicity and speed with small clips, we try inline data logic 
        # but we need to update ModelRouter to handle 'audio_inline'.
        
        # Actually ModelRouter methods are designed for Chat.
        # Creating a specific method in AudioService that calls genai directly might be cleaner 
        # if ModelRouter is too chat-focused. 
        # However, ModelRouter holds the genai configuration.
        
        # Let's ask ModelRouter to do it via a specialized method or direct genai usage if available.
        if model_router.GOOGLE_GENAI_AVAILABLE:
            import google.generativeai as genai
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Inline data
            prompt = "Transcribe this audio verbatim."
            
            response = await model.generate_content_async(
                [
                    prompt,
                    {"mime_type": mime_type, "data": content}
                ]
            )
            return response.text
        else:
            raise RuntimeError("Gemini Native SDK not available")

    async def _transcribe_whisper(self, content: bytes, mime_type: str) -> str:
        """
        Use Whisper API (OpenAI or Groq).
        """
        logger.info("Transcribing audio with Whisper...")
        
        if not self.openai_client:
            raise RuntimeError("OpenAI/Groq client not initialized (check API keys)")

        # OpenAI API expects a file-like object with a name
        # Map mime to extension
        ext_map = {
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/ogg": "ogg",
            "audio/x-m4a": "m4a",
            "audio/mp4": "mp4" # some recorders save audio as mp4
        }
        ext = ext_map.get(mime_type, "mp3")
        filename = f"audio.{ext}"
        
        file_obj = io.BytesIO(content)
        file_obj.name = filename

        # Support Groq specific model if using Groq base_url
        model_name = "whisper-1"
        if "groq" in str(self.openai_client.base_url):
             model_name = "distil-whisper-large-v3-en" # Groq often uses this or whisper-large-v3
             # Let's default to whisper-large-v3 for Groq usually
             model_name = "whisper-large-v3"

        response = await self.openai_client.audio.transcriptions.create(
            file=file_obj,
            model=model_name
        )
        return response.text

# Singleton
audio_service = AudioService()
