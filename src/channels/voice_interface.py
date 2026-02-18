"""
Agent Optimus — Voice Interface (Fase 11: Jarvis Mode).
Abstraction for voice I/O with pluggable providers (STT/TTS).
Supports wake word detection.

Phase 11 completion: real Whisper (OpenAI) and ElevenLabs providers
with graceful fallback when API keys are not configured.
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class VoiceProviderType(str, Enum):
    """Available voice providers."""

    GOOGLE = "google"
    WHISPER = "whisper"
    GROQ_WHISPER = "groq_whisper"  # Groq Whisper (free, fast)
    ELEVENLABS = "elevenlabs"
    EDGE = "edge"  # Microsoft Edge TTS (free)
    STUB = "stub"  # For testing


@dataclass
class VoiceConfig:
    """Configuration for voice interface."""

    stt_provider: VoiceProviderType = VoiceProviderType.GROQ_WHISPER
    tts_provider: VoiceProviderType = VoiceProviderType.EDGE
    language: str = "pt-BR"
    voice_name: str = "optimus"
    speed: float = 1.0
    wake_words: list[str] = field(default_factory=lambda: ["optimus", "hey optimus"])


class VoiceProvider(ABC):
    """Abstract base class for voice providers."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Convert speech to text (STT)."""
        ...

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Convert text to speech (TTS)."""
        ...


class StubVoiceProvider(VoiceProvider):
    """Stub provider for testing — returns placeholder values."""

    async def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        return f"[transcribed: {len(audio_bytes)} bytes]"

    async def synthesize(self, text: str) -> bytes:
        if not text:
            return b""
        return f"[audio: {text[:50]}]".encode("utf-8")


class GoogleVoiceProvider(VoiceProvider):
    """Google Cloud Speech-to-Text / Text-to-Speech. Requires google-cloud-speech."""

    async def transcribe(self, audio_bytes: bytes) -> str:
        # Requires google-cloud-speech SDK — stub for now
        logger.warning("Google STT not yet implemented, using stub")
        return f"[google-stt: {len(audio_bytes)} bytes]"

    async def synthesize(self, text: str) -> bytes:
        # Requires google-cloud-texttospeech SDK — stub for now
        logger.warning("Google TTS not yet implemented, using stub")
        return f"[google-tts: {text[:50]}]".encode("utf-8")


class WhisperProvider(VoiceProvider):
    """
    OpenAI Whisper for STT.

    Uses the OpenAI API (POST /v1/audio/transcriptions).
    Requires OPENAI_API_KEY environment variable.
    Falls back to stub if API key is not configured.
    """

    OPENAI_API_URL = "https://api.openai.com/v1/audio/transcriptions"

    async def transcribe(self, audio_bytes: bytes) -> str:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            logger.debug("Whisper STT: OPENAI_API_KEY not set, using stub fallback")
            return f"[whisper-stub: {len(audio_bytes)} bytes]"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.OPENAI_API_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": ("audio.webm", audio_bytes, "audio/webm")},
                    data={"model": "whisper-1", "language": "pt"},
                )
                response.raise_for_status()
                result = response.json()
                text = result.get("text", "")
                logger.info(f"Whisper STT: transcribed {len(audio_bytes)} bytes → '{text[:80]}'")
                return text

        except httpx.HTTPError as e:
            logger.error(f"Whisper STT error: {e}")
            return f"[whisper-error: {e}]"

    async def synthesize(self, text: str) -> bytes:
        # Whisper is STT only — use stub for TTS
        return f"[no-tts: {text[:50]}]".encode("utf-8")


class GroqWhisperProvider(VoiceProvider):
    """
    Groq Whisper for STT — free and fast.

    Uses the Groq API (POST /openai/v1/audio/transcriptions).
    Requires GROQ_API_KEY environment variable.
    Falls back to stub if API key is not configured.
    Model: whisper-large-v3
    """

    GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def transcribe(self, audio_bytes: bytes) -> str:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            logger.debug("Groq Whisper STT: GROQ_API_KEY not set, using stub fallback")
            return f"[groq-whisper-stub: {len(audio_bytes)} bytes]"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.GROQ_API_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": ("audio.webm", audio_bytes, "audio/webm")},
                    data={"model": "whisper-large-v3", "language": "pt"},
                )
                response.raise_for_status()
                result = response.json()
                text = result.get("text", "")
                logger.info(f"Groq Whisper STT: transcribed {len(audio_bytes)} bytes → '{text[:80]}'")
                return text

        except httpx.HTTPError as e:
            logger.error(f"Groq Whisper STT error: {e}")
            return f"[groq-whisper-error: {e}]"

    async def synthesize(self, text: str) -> bytes:
        # Groq Whisper is STT only — use stub for TTS
        return f"[no-tts: {text[:50]}]".encode("utf-8")


class ElevenLabsProvider(VoiceProvider):
    """
    ElevenLabs for high-quality TTS.

    Uses the ElevenLabs API (POST /v1/text-to-speech/{voice_id}).
    Requires ELEVENLABS_API_KEY and optionally ELEVENLABS_VOICE_ID.
    Falls back to stub if API key is not configured.
    """

    ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (default ElevenLabs voice)

    async def transcribe(self, audio_bytes: bytes) -> str:
        # ElevenLabs is TTS only — use stub for STT
        return f"[no-stt: {len(audio_bytes)} bytes]"

    async def synthesize(self, text: str) -> bytes:
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            logger.debug("ElevenLabs TTS: ELEVENLABS_API_KEY not set, using stub fallback")
            return f"[elevenlabs-stub: {text[:50]}]".encode("utf-8")

        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", self.DEFAULT_VOICE_ID)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ELEVENLABS_API_URL}/{voice_id}",
                    headers={
                        "xi-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    },
                )
                response.raise_for_status()
                audio_bytes = response.content
                logger.info(f"ElevenLabs TTS: synthesized '{text[:50]}' → {len(audio_bytes)} bytes")
                return audio_bytes

        except httpx.HTTPError as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            return f"[elevenlabs-error: {e}]".encode("utf-8")


class EdgeTTSProvider(VoiceProvider):
    """
    Microsoft Edge TTS — free, high-quality neural voices.

    Requires edge-tts package: pip install edge-tts
    No API key needed, completely free.
    Supports 400+ voices in 100+ languages.
    """

    async def transcribe(self, audio_bytes: bytes) -> str:
        # Edge TTS doesn't support STT — use stub
        return f"[edge-no-stt: {len(audio_bytes)} bytes]"

    async def synthesize(self, text: str) -> bytes:
        try:
            import edge_tts
        except ImportError:
            logger.warning("edge-tts not installed, using stub fallback. Install: pip install edge-tts")
            return f"[edge-stub: {text[:50]}]".encode("utf-8")

        # Default to Brazilian Portuguese voice
        voice = os.environ.get("EDGE_TTS_VOICE", "pt-BR-AntonioNeural")

        try:
            # Create a temporary file to store the audio
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Generate speech
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp_path)

            # Read the audio bytes
            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            logger.info(f"Edge TTS: synthesized '{text[:50]}' → {len(audio_bytes)} bytes (voice={voice})")
            return audio_bytes

        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            return f"[edge-error: {e}]".encode("utf-8")


# Provider registry
PROVIDERS: dict[VoiceProviderType, type[VoiceProvider]] = {
    VoiceProviderType.STUB: StubVoiceProvider,
    VoiceProviderType.GOOGLE: GoogleVoiceProvider,
    VoiceProviderType.WHISPER: WhisperProvider,
    VoiceProviderType.GROQ_WHISPER: GroqWhisperProvider,
    VoiceProviderType.ELEVENLABS: ElevenLabsProvider,
    VoiceProviderType.EDGE: EdgeTTSProvider,
}


class VoiceInterface:
    """
    Voice interaction interface for Jarvis-like experience.

    Features:
    - Pluggable STT/TTS providers
    - Wake word detection
    - Configurable language, voice, and speed
    """

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()
        self._stt = self._create_provider(self.config.stt_provider)
        self._tts = self._create_provider(self.config.tts_provider)

    def _create_provider(self, provider_type: VoiceProviderType) -> VoiceProvider:
        """Create a voice provider instance."""
        provider_class = PROVIDERS.get(provider_type, StubVoiceProvider)
        return provider_class()

    async def listen(self, audio_bytes: bytes) -> str:
        """
        Convert audio to text using the configured STT provider.

        Args:
            audio_bytes: Raw audio data

        Returns:
            Transcribed text
        """
        if not audio_bytes:
            return ""

        text = await self._stt.transcribe(audio_bytes)
        logger.debug(f"Voice STT: {len(audio_bytes)} bytes → '{text[:80]}'")
        return text

    async def speak(self, text: str) -> bytes:
        """
        Convert text to audio using the configured TTS provider.

        Args:
            text: Text to synthesize

        Returns:
            Audio bytes
        """
        if not text:
            return b""

        audio = await self._tts.synthesize(text)
        logger.debug(f"Voice TTS: '{text[:50]}' → {len(audio)} bytes")
        return audio

    def detect_wake_word(self, text: str) -> bool:
        """
        Check if the text contains a wake word.

        Args:
            text: Transcribed text to check

        Returns:
            True if wake word detected
        """
        text_lower = text.lower().strip()
        for wake_word in self.config.wake_words:
            if wake_word in text_lower:
                return True
        return False

    def strip_wake_word(self, text: str) -> str:
        """Remove wake word from text to get the actual command."""
        text_clean = text
        for wake_word in sorted(self.config.wake_words, key=len, reverse=True):
            pattern = re.compile(re.escape(wake_word), re.IGNORECASE)
            text_clean = pattern.sub("", text_clean)
        return text_clean.strip().lstrip(",").strip()

    def update_config(self, **kwargs) -> None:
        """Update voice configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Recreate providers if changed
        if "stt_provider" in kwargs:
            self._stt = self._create_provider(self.config.stt_provider)
        if "tts_provider" in kwargs:
            self._tts = self._create_provider(self.config.tts_provider)


# Singleton
voice_interface = VoiceInterface()
