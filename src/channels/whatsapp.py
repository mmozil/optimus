"""
Agent Optimus — WhatsApp Channel Adapter.
Uses Evolution API for WhatsApp Business integration.
"""

import logging

import httpx

from src.channels.base_channel import (
    BaseChannel, ChannelType, IncomingMessage, OutgoingMessage,
)

logger = logging.getLogger(__name__)


class WhatsAppChannel(BaseChannel):
    """
    WhatsApp channel adapter via Evolution API.
    Supports text, media, groups. Webhook-based for incoming messages.
    Requires EVOLUTION_API_URL and EVOLUTION_API_KEY in config.
    """

    def __init__(self, config: dict | None = None):
        super().__init__(ChannelType.WHATSAPP, config)
        self.api_url = (config or {}).get("api_url", "http://localhost:8080")
        self.api_key = (config or {}).get("api_key", "")
        self.instance_name = (config or {}).get("instance_name", "optimus")

    async def start(self):
        """Initialize WhatsApp instance via Evolution API."""
        try:
            async with httpx.AsyncClient() as client:
                # Check if instance exists, create if needed
                response = await client.get(
                    f"{self.api_url}/instance/fetchInstances",
                    headers={"apikey": self.api_key},
                )

                if response.status_code == 200:
                    instances = response.json()
                    exists = any(i.get("instance", {}).get("instanceName") == self.instance_name
                                 for i in instances)

                    if not exists:
                        await self._create_instance()

                    self._running = True
                    logger.info(f"[WhatsApp] Instance '{self.instance_name}' connected")
                else:
                    logger.error(f"[WhatsApp] API check failed: {response.status_code}")

        except Exception as e:
            logger.error(f"[WhatsApp] Failed to start: {e}")

    async def stop(self):
        """Disconnect WhatsApp instance."""
        self._running = False
        logger.info("[WhatsApp] Disconnected")

    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message via WhatsApp (Evolution API)."""
        try:
            async with httpx.AsyncClient() as client:
                if message.media_url:
                    # Send media message
                    media_endpoint = {
                        "image": "sendMedia",
                        "audio": "sendWhatsAppAudio",
                        "video": "sendMedia",
                        "document": "sendMedia",
                    }.get(message.media_type or "document", "sendMedia")

                    payload = {
                        "number": message.chat_id,
                        "mediatype": message.media_type or "document",
                        "media": message.media_url,
                        "caption": message.text,
                    }

                    response = await client.post(
                        f"{self.api_url}/message/{media_endpoint}/{self.instance_name}",
                        json=payload,
                        headers={"apikey": self.api_key},
                    )
                else:
                    # Send text message
                    payload = {
                        "number": message.chat_id,
                        "text": message.text,
                    }

                    response = await client.post(
                        f"{self.api_url}/message/sendText/{self.instance_name}",
                        json=payload,
                        headers={"apikey": self.api_key},
                    )

                if response.status_code in (200, 201):
                    return True

                logger.warning(f"[WhatsApp] Send response: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"[WhatsApp] Send failed: {e}")
            return False

    async def process_webhook(self, payload: dict) -> OutgoingMessage | None:
        """
        Process incoming webhook from Evolution API.
        Call this from your FastAPI webhook endpoint.
        """
        event = payload.get("event", "")

        if event != "messages.upsert":
            return None

        data = payload.get("data", {})
        key = data.get("key", {})
        message_data = data.get("message", {})

        # Skip status messages and own messages
        if key.get("fromMe", False):
            return None

        # Extract text
        text = (
            message_data.get("conversation", "")
            or message_data.get("extendedTextMessage", {}).get("text", "")
        )

        # Extract media if present
        media_type = None
        media_url = None
        if "imageMessage" in message_data:
            media_type = "image"
        elif "audioMessage" in message_data:
            media_type = "audio"
        elif "documentMessage" in message_data:
            media_type = "document"

        remote_jid = key.get("remoteJid", "")
        is_group = "@g.us" in remote_jid

        incoming = IncomingMessage(
            channel=ChannelType.WHATSAPP,
            chat_id=remote_jid,
            user_id=data.get("pushName", remote_jid.split("@")[0]),
            user_name=data.get("pushName", ""),
            text=text,
            media_type=media_type,
            media_url=media_url,
            is_group=is_group,
            raw=payload,
        )

        return await self.handle_incoming(incoming)

    async def _create_instance(self):
        """Create a new Evolution API instance."""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "instanceName": self.instance_name,
                    "integration": "WHATSAPP-BAILEYS",
                    "qrcode": True,
                }

                response = await client.post(
                    f"{self.api_url}/instance/create",
                    json=payload,
                    headers={"apikey": self.api_key},
                )

                if response.status_code in (200, 201):
                    result = response.json()
                    qr = result.get("qrcode", {}).get("base64", "")
                    if qr:
                        logger.info(f"[WhatsApp] QR Code generated. Scan to connect.")
                    logger.info(f"[WhatsApp] Instance '{self.instance_name}' created")
                else:
                    logger.error(f"[WhatsApp] Create failed: {response.text}")

        except Exception as e:
            logger.error(f"[WhatsApp] Instance creation failed: {e}")
