"""
Agent Optimus — Voice Interface (Fase 11: Jarvis Mode).
Abstraction for voice I/O with pluggable providers (STT/TTS).
Supports wake word detection. MVP with stubs - real providers added later.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VoiceProviderType(str, Enum):
    """Available voice providers."""

    GOOGLE = "google"
    WHISPER = "whisper"
    ELEVENLABS = "elevenlabs"
    STUB = "stub"  # For testing


@dataclass
class VoiceConfig:
    """Configuration for voice interface."""

    stt_provider: VoiceProviderType = VoiceProviderType.STUB
    tts_provider: VoiceProviderType = VoiceProviderType.STUB
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
        # TODO: Implement with google-cloud-speech
        logger.warning("Google STT not yet implemented, using stub")
        return f"[google-stt: {len(audio_bytes)} bytes]"

    async def synthesize(self, text: str) -> bytes:
        # TODO: Implement with google-cloud-texttospeech
        logger.warning("Google TTS not yet implemented, using stub")
        return f"[google-tts: {text[:50]}]".encode("utf-8")


class WhisperProvider(VoiceProvider):
    """OpenAI Whisper for STT. Requires openai."""

    async def transcribe(self, audio_bytes: bytes) -> str:
        # TODO: Implement with openai whisper API
        logger.warning("Whisper STT not yet implemented, using stub")
        return f"[whisper: {len(audio_bytes)} bytes]"

    async def synthesize(self, text: str) -> bytes:
        # Whisper is STT only — use stub for TTS
        return f"[no-tts: {text[:50]}]".encode("utf-8")


class ElevenLabsProvider(VoiceProvider):
    """ElevenLabs for high-quality TTS. Requires elevenlabs."""

    async def transcribe(self, audio_bytes: bytes) -> str:
        # ElevenLabs is TTS only — use stub for STT
        return f"[no-stt: {len(audio_bytes)} bytes]"

    async def synthesize(self, text: str) -> bytes:
        # TODO: Implement with elevenlabs API
        logger.warning("ElevenLabs TTS not yet implemented, using stub")
        return f"[elevenlabs: {text[:50]}]".encode("utf-8")


# Provider registry
PROVIDERS: dict[VoiceProviderType, type[VoiceProvider]] = {
    VoiceProviderType.STUB: StubVoiceProvider,
    VoiceProviderType.GOOGLE: GoogleVoiceProvider,
    VoiceProviderType.WHISPER: WhisperProvider,
    VoiceProviderType.ELEVENLABS: ElevenLabsProvider,
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
