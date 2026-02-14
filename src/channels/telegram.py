"""
Agent Optimus — Telegram Channel Adapter.
Uses python-telegram-bot for Telegram Bot API integration.
"""

import logging

from src.channels.base_channel import (
    BaseChannel, ChannelType, IncomingMessage, OutgoingMessage,
)

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """
    Telegram channel adapter.
    Handles private chats, groups, media, and command parsing.
    Requires TELEGRAM_BOT_TOKEN in config.
    """

    def __init__(self, config: dict | None = None):
        super().__init__(ChannelType.TELEGRAM, config)
        self.bot_token = (config or {}).get("bot_token", "")
        self._app = None

    async def start(self):
        """Start Telegram bot with polling."""
        if not self.bot_token:
            logger.error("[Telegram] No bot_token configured")
            return

        try:
            from telegram.ext import (
                ApplicationBuilder,
                CommandHandler,
                MessageHandler,
                filters,
            )

            self._app = ApplicationBuilder().token(self.bot_token).build()

            # Register handlers
            self._app.add_handler(CommandHandler("start", self._cmd_start))
            self._app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text)
            )
            self._app.add_handler(
                MessageHandler(filters.PHOTO | filters.Document.ALL, self._on_media)
            )

            self._running = True
            logger.info("[Telegram] Bot started — polling mode")

            # Start polling (non-blocking)
            await self._app.initialize()
            await self._app.start()
            await self._app.updater.start_polling()

        except ImportError:
            logger.error("[Telegram] python-telegram-bot not installed. Run: pip install python-telegram-bot")
        except Exception as e:
            logger.error(f"[Telegram] Failed to start: {e}")

    async def stop(self):
        """Stop Telegram bot."""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            self._running = False
            logger.info("[Telegram] Bot stopped")

    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message via Telegram."""
        if not self._app:
            return False

        try:
            parse_mode = "MarkdownV2" if message.parse_mode == "markdown" else "HTML"

            if message.media_url and message.media_type == "image":
                await self._app.bot.send_photo(
                    chat_id=int(message.chat_id),
                    photo=message.media_url,
                    caption=message.text[:1024],
                    parse_mode=parse_mode,
                )
            else:
                await self._app.bot.send_message(
                    chat_id=int(message.chat_id),
                    text=message.text,
                    parse_mode=parse_mode,
                    reply_to_message_id=int(message.reply_to_id) if message.reply_to_id else None,
                )
            return True

        except Exception as e:
            logger.error(f"[Telegram] Send failed: {e}")
            return False

    # ============================================
    # Internal Handlers
    # ============================================

    async def _cmd_start(self, update, context):
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 **Agent Optimus** conectado!\n\n"
            "Envie qualquer mensagem para começar.\n"
            "Use /status para ver o status dos agents.",
            parse_mode="Markdown",
        )

    async def _on_text(self, update, context):
        """Handle text messages."""
        msg = update.message
        chat = msg.chat

        incoming = IncomingMessage(
            channel=ChannelType.TELEGRAM,
            chat_id=str(chat.id),
            user_id=str(msg.from_user.id),
            user_name=msg.from_user.first_name or msg.from_user.username or "",
            text=msg.text,
            is_group=chat.type in ("group", "supergroup"),
            group_name=chat.title if chat.type in ("group", "supergroup") else None,
            reply_to_id=str(msg.reply_to_message.message_id) if msg.reply_to_message else None,
            raw=msg.to_dict(),
        )

        response = await self.handle_incoming(incoming)
        if response:
            response.chat_id = str(chat.id)
            await self.send_message(response)

    async def _on_media(self, update, context):
        """Handle media messages (photos, documents)."""
        msg = update.message
        chat = msg.chat

        # Determine media type and URL
        media_type = None
        media_url = None

        if msg.photo:
            media_type = "image"
            file = await msg.photo[-1].get_file()
            media_url = file.file_path
        elif msg.document:
            media_type = "document"
            file = await msg.document.get_file()
            media_url = file.file_path

        incoming = IncomingMessage(
            channel=ChannelType.TELEGRAM,
            chat_id=str(chat.id),
            user_id=str(msg.from_user.id),
            user_name=msg.from_user.first_name or "",
            text=msg.caption or "",
            media_url=media_url,
            media_type=media_type,
            is_group=chat.type in ("group", "supergroup"),
            raw=msg.to_dict(),
        )

        response = await self.handle_incoming(incoming)
        if response:
            response.chat_id = str(chat.id)
            await self.send_message(response)
