"""
Agent Optimus — Voice API (FASE 0 #18: Voice Interface).
REST endpoints for STT, TTS, and voice command processing.
"""

import base64
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.channels.voice_interface import VoiceProviderType, voice_interface

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


# ============================================
# Request/Response Models
# ============================================


class VoiceListenRequest(BaseModel):
    """Request to transcribe audio."""

    audio_base64: str = Field(..., description="Base64-encoded audio data")


class VoiceListenResponse(BaseModel):
    """Response containing transcribed text."""

    text: str
    wake_word_detected: bool = False


class VoiceSpeakRequest(BaseModel):
    """Request to synthesize speech."""

    text: str = Field(..., description="Text to convert to speech")


class VoiceSpeakResponse(BaseModel):
    """Response containing synthesized audio."""

    audio_base64: str


class VoiceCommandRequest(BaseModel):
    """Request to process voice command."""

    audio_base64: str = Field(..., description="Base64-encoded audio data")
    user_id: str = Field(..., description="User ID for context")
    session_id: str | None = Field(None, description="Session ID for context")


class VoiceCommandResponse(BaseModel):
    """Response from voice command processing."""

    transcribed_text: str
    wake_word_detected: bool
    command: str | None
    response: str | None
    response_audio_base64: str | None


class VoiceConfigResponse(BaseModel):
    """Current voice configuration."""

    stt_provider: str
    tts_provider: str
    language: str
    wake_words: list[str]
    voice_name: str


class VoiceConfigUpdateRequest(BaseModel):
    """Request to update voice configuration."""

    stt_provider: VoiceProviderType | None = None
    tts_provider: VoiceProviderType | None = None
    wake_words: list[str] | None = None
    language: str | None = None


# ============================================
# API Endpoints
# ============================================


@router.post("/listen", response_model=VoiceListenResponse)
async def voice_listen(request: VoiceListenRequest) -> VoiceListenResponse:
    """
    Convert audio to text using STT (Speech-to-Text).

    Supports multiple providers: Whisper (OpenAI), Google Cloud, Stub.
    """
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio_base64)

        # Transcribe using configured STT provider
        text = await voice_interface.listen(audio_bytes)

        # Check for wake word
        wake_word_detected = voice_interface.detect_wake_word(text)

        logger.info(
            f"Voice STT: {len(audio_bytes)} bytes → '{text[:50]}' (wake_word={wake_word_detected})"
        )

        return VoiceListenResponse(
            text=text,
            wake_word_detected=wake_word_detected,
        )

    except Exception as e:
        logger.error(f"Voice STT failed: {e}")
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")


@router.post("/speak", response_model=VoiceSpeakResponse)
async def voice_speak(request: VoiceSpeakRequest) -> VoiceSpeakResponse:
    """
    Convert text to audio using TTS (Text-to-Speech).

    Supports multiple providers: ElevenLabs, Google Cloud, Stub.
    """
    try:
        # Synthesize using configured TTS provider
        audio_bytes = await voice_interface.speak(request.text)

        # Encode to base64
        audio_base64 = base64.b64encode(audio_bytes).decode()

        logger.info(f"Voice TTS: '{request.text[:50]}' → {len(audio_bytes)} bytes")

        return VoiceSpeakResponse(audio_base64=audio_base64)

    except Exception as e:
        logger.error(f"Voice TTS failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")


@router.post("/command", response_model=VoiceCommandResponse)
async def voice_command(request: VoiceCommandRequest) -> VoiceCommandResponse:
    """
    Process voice command with wake word detection.

    Flow:
    1. Transcribe audio → text
    2. Detect wake word
    3. If wake word detected, strip it and route to agent
    4. Return agent response + TTS audio
    """
    try:
        # 1. Transcribe audio
        audio_bytes = base64.b64decode(request.audio_base64)
        text = await voice_interface.listen(audio_bytes)

        # 2. Detect wake word
        wake_word_detected = voice_interface.detect_wake_word(text)

        command = None
        response = None
        response_audio_base64 = None

        # 3. Process command if wake word detected
        if wake_word_detected:
            command = voice_interface.strip_wake_word(text)

            # Route to gateway for agent processing
            try:
                from src.core.gateway import gateway

                result = await gateway.route_message(
                    message=command,
                    context={
                        "user_id": request.user_id,
                        "session_id": request.session_id or request.user_id,
                        "channel": "voice",
                    },
                )

                response = result.get("content", "")

                # 4. Synthesize response to audio
                if response:
                    response_audio = await voice_interface.speak(response)
                    response_audio_base64 = base64.b64encode(response_audio).decode()

            except Exception as e:
                logger.error(f"Voice command routing failed: {e}")
                response = f"Erro ao processar comando: {e}"

        logger.info(
            f"Voice command: '{text[:50]}' → wake_word={wake_word_detected}, response={len(response or '') > 0}"
        )

        return VoiceCommandResponse(
            transcribed_text=text,
            wake_word_detected=wake_word_detected,
            command=command,
            response=response,
            response_audio_base64=response_audio_base64,
        )

    except Exception as e:
        logger.error(f"Voice command processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Command processing failed: {e}")


@router.get("/config", response_model=VoiceConfigResponse)
async def get_voice_config() -> VoiceConfigResponse:
    """
    Get current voice interface configuration.

    Returns STT/TTS providers, wake words, and language settings.
    """
    try:
        config = voice_interface.config

        return VoiceConfigResponse(
            stt_provider=config.stt_provider.value,
            tts_provider=config.tts_provider.value,
            language=config.language,
            wake_words=config.wake_words,
            voice_name=config.voice_name,
        )

    except Exception as e:
        logger.error(f"Get voice config failed: {e}")
        raise HTTPException(status_code=500, detail=f"Config retrieval failed: {e}")


@router.put("/config")
async def update_voice_config(request: VoiceConfigUpdateRequest) -> dict[str, Any]:
    """
    Update voice interface configuration.

    Allows changing STT/TTS providers, wake words, and language at runtime.
    """
    try:
        # Build update dict (only include non-None fields)
        updates = {}
        if request.stt_provider is not None:
            updates["stt_provider"] = request.stt_provider
        if request.tts_provider is not None:
            updates["tts_provider"] = request.tts_provider
        if request.wake_words is not None:
            updates["wake_words"] = request.wake_words
        if request.language is not None:
            updates["language"] = request.language

        # Apply updates
        voice_interface.update_config(**updates)

        logger.info(f"Voice config updated: {updates}")

        return {
            "success": True,
            "updated_fields": list(updates.keys()),
            "message": "Voice configuration updated successfully",
        }

    except Exception as e:
        logger.error(f"Update voice config failed: {e}")
        raise HTTPException(status_code=500, detail=f"Config update failed: {e}")
