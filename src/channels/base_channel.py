"""
Agent Optimus — Base Channel.
Abstract interface that all channel adapters must implement.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    WEBCHAT = "webchat"


@dataclass
class IncomingMessage:
    """Normalized incoming message from any channel."""
    id: str = field(default_factory=lambda: str(uuid4()))
    channel: ChannelType = ChannelType.WEBCHAT
    chat_id: str = ""  # channel-specific chat/conversation ID
    user_id: str = ""  # channel-specific user ID
    user_name: str = ""
    text: str = ""
    media_url: str | None = None  # URL to attached media
    media_type: str | None = None  # image, audio, video, document
    reply_to_id: str | None = None  # ID of message being replied to
    is_group: bool = False
    group_name: str | None = None
    raw: dict = field(default_factory=dict)  # Original message payload
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OutgoingMessage:
    """Normalized outgoing message to any channel."""
    text: str
    chat_id: str
    reply_to_id: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    parse_mode: str = "markdown"  # markdown | html | plain
    metadata: dict = field(default_factory=dict)


class BaseChannel(ABC):
    """
    Abstract base for all channel adapters.
    Each channel must implement:
    - start(): Initialize and connect
    - stop(): Disconnect gracefully
    - send_message(): Send a message
    - _on_message(): Handle incoming messages (internal)
    """

    def __init__(self, channel_type: ChannelType, config: dict | None = None):
        self.channel_type = channel_type
        self.config = config or {}
        self._running = False
        self._message_handler = None  # Callback for processing messages

    @property
    def name(self) -> str:
        return self.channel_type.value

    @property
    def is_running(self) -> bool:
        return self._running

    def set_message_handler(self, handler):
        """Set the callback function for processing incoming messages.
        Handler signature: async def handler(message: IncomingMessage) -> OutgoingMessage
        """
        self._message_handler = handler

    @abstractmethod
    async def start(self):
        """Start the channel adapter (connect, start polling/webhook)."""
        ...

    @abstractmethod
    async def stop(self):
        """Stop the channel adapter gracefully."""
        ...

    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message through the channel. Returns True on success."""
        ...

    async def handle_incoming(self, message: IncomingMessage) -> OutgoingMessage | None:
        """Process an incoming message through the registered handler."""
        if not self._message_handler:
            logger.warning(f"[{self.name}] No message handler registered")
            return None

        try:
            logger.info(f"[{self.name}] Incoming message", extra={"props": {
                "chat_id": message.chat_id, "user": message.user_name,
                "text_length": len(message.text), "is_group": message.is_group,
            }})

            response = await self._message_handler(message)
            return response

        except Exception as e:
            logger.error(f"[{self.name}] Message handling failed: {e}")
            return OutgoingMessage(
                text="❌ Erro ao processar mensagem. Tente novamente.",
                chat_id=message.chat_id,
                reply_to_id=message.id,
            )

    def status(self) -> dict:
        """Get channel status."""
        return {
            "channel": self.name,
            "running": self._running,
            "has_handler": self._message_handler is not None,
        }
