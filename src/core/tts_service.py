"""
Agent Optimus — TTS Service (Vivaldi-inspired).

System-level TTS: converts agent text responses to audio automatically
based on user's tts_mode preference. No LLM tool call needed.

Modes:
  off         — no audio generated (default)
  always      — every chat response gets audio
  on_request  — only when user explicitly asks ("me manda um áudio")
"""

import base64
import logging
import re

logger = logging.getLogger(__name__)

# Max chars to synthesize directly (longer texts get summarized)
TTS_MAX_CHARS = 600


def strip_markdown(text: str) -> str:
    """Remove markdown formatting so TTS reads clean prose."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Remove links [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove list markers
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove uncertainty divider and below
    text = text.split("\n---\n")[0]
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def prepare_tts_text(text: str, max_chars: int = TTS_MAX_CHARS) -> str:
    """
    Prepare text for TTS synthesis:
    1. Strip markdown
    2. Extract [[tts:text]]...[[/tts:text]] directive if present
    3. Truncate to max_chars (at sentence boundary if possible)
    """
    # Check for explicit TTS directive
    tts_match = re.search(r"\[\[tts:text\]\]([\s\S]*?)\[\[/tts:text\]\]", text)
    if tts_match:
        return strip_markdown(tts_match.group(1)).strip()

    clean = strip_markdown(text)

    if len(clean) <= max_chars:
        return clean

    # Truncate at sentence boundary
    truncated = clean[:max_chars]
    last_period = max(
        truncated.rfind(". "),
        truncated.rfind("! "),
        truncated.rfind("? "),
        truncated.rfind(".\n"),
    )
    if last_period > max_chars // 2:
        return truncated[:last_period + 1].strip()

    return truncated.strip() + "..."


async def text_to_audio_base64(text: str, voice: str = "pt-BR-AntonioNeural") -> str | None:
    """
    Convert text to base64-encoded MP3 audio.
    Returns None on failure (graceful — caller should not crash).
    """
    if not text or not text.strip():
        return None

    try:
        import os
        os.environ.setdefault("EDGE_TTS_VOICE", voice)

        from src.channels.voice_interface import voice_interface
        tts_text = prepare_tts_text(text)

        if not tts_text:
            return None

        audio_bytes = await voice_interface.speak(tts_text)

        # Validate: real audio starts with ID3 or MP3 frame, not stub text
        if not audio_bytes or audio_bytes[:3] in (b"[ed", b"[no", b"[st", b"[go"):
            logger.warning(f"TTS returned stub instead of audio: {audio_bytes[:30]}")
            return None

        return base64.b64encode(audio_bytes).decode()

    except Exception as e:
        logger.warning(f"TTS synthesis failed: {e}")
        return None