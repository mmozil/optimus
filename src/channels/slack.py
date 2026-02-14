"""
Agent Optimus — Slack Channel Adapter.
Uses Slack Bolt for Slack workspace integration.
"""

import logging

from src.channels.base_channel import (
    BaseChannel, ChannelType, IncomingMessage, OutgoingMessage,
)

logger = logging.getLogger(__name__)


class SlackChannel(BaseChannel):
    """
    Slack channel adapter via Slack Bolt.
    Supports channels, threads, DMs, mentions, and slash commands.
    Requires SLACK_BOT_TOKEN and SLACK_APP_TOKEN in config.
    """

    def __init__(self, config: dict | None = None):
        super().__init__(ChannelType.SLACK, config)
        self.bot_token = (config or {}).get("bot_token", "")
        self.app_token = (config or {}).get("app_token", "")
        self.signing_secret = (config or {}).get("signing_secret", "")
        self._app = None
        self._handler = None

    async def start(self):
        """Start Slack bot with Socket Mode."""
        if not self.bot_token or not self.app_token:
            logger.error("[Slack] Missing bot_token or app_token")
            return

        try:
            from slack_bolt.async_app import AsyncApp
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

            self._app = AsyncApp(
                token=self.bot_token,
                signing_secret=self.signing_secret,
            )

            # Register event handlers
            self._app.event("message")(self._on_message)
            self._app.event("app_mention")(self._on_mention)

            # Register slash commands
            self._app.command("/optimus")(self._on_slash_command)

            # Start Socket Mode
            self._handler = AsyncSocketModeHandler(self._app, self.app_token)
            await self._handler.start_async()

            self._running = True
            logger.info("[Slack] Bot started — Socket Mode")

        except ImportError:
            logger.error("[Slack] slack-bolt not installed. Run: pip install slack-bolt")
        except Exception as e:
            logger.error(f"[Slack] Failed to start: {e}")

    async def stop(self):
        """Stop Slack bot."""
        if self._handler:
            await self._handler.close_async()
        self._running = False
        logger.info("[Slack] Bot stopped")

    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message via Slack."""
        if not self._app:
            return False

        try:
            kwargs = {
                "channel": message.chat_id,
                "text": message.text,
            }

            # Support threading
            thread_ts = message.metadata.get("thread_ts")
            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            # Support blocks for rich formatting
            blocks = message.metadata.get("blocks")
            if blocks:
                kwargs["blocks"] = blocks

            await self._app.client.chat_postMessage(**kwargs)
            return True

        except Exception as e:
            logger.error(f"[Slack] Send failed: {e}")
            return False

    # ============================================
    # Event Handlers
    # ============================================

    async def _on_message(self, event, say):
        """Handle regular messages (DMs and channels where bot is added)."""
        # Skip bot messages and message changes
        if event.get("bot_id") or event.get("subtype"):
            return

        incoming = self._parse_event(event)
        response = await self.handle_incoming(incoming)

        if response:
            kwargs = {"text": response.text}
            # Reply in thread if original was in thread
            if event.get("thread_ts"):
                kwargs["thread_ts"] = event["thread_ts"]
            await say(**kwargs)

    async def _on_mention(self, event, say):
        """Handle @mention events."""
        incoming = self._parse_event(event)
        # Remove bot mention from text
        incoming.text = incoming.text.split(">", 1)[-1].strip() if ">" in incoming.text else incoming.text

        response = await self.handle_incoming(incoming)
        if response:
            kwargs = {"text": response.text}
            if event.get("thread_ts"):
                kwargs["thread_ts"] = event["thread_ts"]
            elif event.get("ts"):
                kwargs["thread_ts"] = event["ts"]  # Start a new thread
            await say(**kwargs)

    async def _on_slash_command(self, ack, command, say):
        """Handle /optimus slash commands."""
        await ack()

        text = command.get("text", "").strip()
        user_name = command.get("user_name", "")
        channel_id = command.get("channel_id", "")

        incoming = IncomingMessage(
            channel=ChannelType.SLACK,
            chat_id=channel_id,
            user_id=command.get("user_id", ""),
            user_name=user_name,
            text=f"/optimus {text}" if text else "/optimus",
            raw=command,
        )

        response = await self.handle_incoming(incoming)
        if response:
            await say(text=response.text)

    # ============================================
    # Helpers
    # ============================================

    def _parse_event(self, event: dict) -> IncomingMessage:
        """Parse a Slack event into an IncomingMessage."""
        channel_type = event.get("channel_type", "")

        return IncomingMessage(
            channel=ChannelType.SLACK,
            chat_id=event.get("channel", ""),
            user_id=event.get("user", ""),
            user_name=event.get("user", ""),
            text=event.get("text", ""),
            is_group=channel_type in ("channel", "group"),
            reply_to_id=event.get("thread_ts"),
            raw=event,
        )

    async def get_user_info(self, user_id: str) -> dict:
        """Get Slack user info for display names."""
        if not self._app:
            return {}

        try:
            result = await self._app.client.users_info(user=user_id)
            user = result["user"]
            return {
                "name": user.get("real_name", user.get("name", "")),
                "display_name": user.get("profile", {}).get("display_name", ""),
                "avatar": user.get("profile", {}).get("image_72", ""),
            }
        except Exception:
            return {"name": user_id}
