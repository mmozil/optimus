"""
Tests for Phase 4 — Channels: Base, WebChat, Chat Commands.
(Telegram, WhatsApp, Slack require real API tokens — tested manually)
"""

import pytest
from uuid import uuid4

from src.channels.base_channel import (
    BaseChannel, ChannelType, IncomingMessage, OutgoingMessage,
)
from src.channels.webchat import WebChatChannel
from src.channels.chat_commands import ChatCommandHandler, COMMANDS


# ============================================
# IncomingMessage / OutgoingMessage Tests
# ============================================
class TestMessages:
    def test_incoming_message_defaults(self):
        msg = IncomingMessage(text="Hello")
        assert msg.channel == ChannelType.WEBCHAT
        assert msg.text == "Hello"
        assert msg.is_group is False
        assert msg.media_url is None

    def test_incoming_telegram_message(self):
        msg = IncomingMessage(
            channel=ChannelType.TELEGRAM,
            chat_id="12345",
            user_name="marcelo",
            text="Test",
            is_group=True,
            group_name="Dev Team",
        )
        assert msg.channel == ChannelType.TELEGRAM
        assert msg.is_group is True
        assert msg.group_name == "Dev Team"

    def test_incoming_slack_message(self):
        msg = IncomingMessage(
            channel=ChannelType.SLACK,
            chat_id="C01ABC",
            user_id="U01XYZ",
            text="@optimus check this",
        )
        assert msg.channel == ChannelType.SLACK

    def test_outgoing_message(self):
        msg = OutgoingMessage(text="Response", chat_id="123")
        assert msg.parse_mode == "markdown"

    def test_outgoing_with_media(self):
        msg = OutgoingMessage(
            text="Here's a file",
            chat_id="123",
            media_url="https://example.com/file.pdf",
            media_type="document",
        )
        assert msg.media_type == "document"


# ============================================
# WebChat Channel Tests
# ============================================
class TestWebChatChannel:
    def setup_method(self):
        self.webchat = WebChatChannel()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        await self.webchat.start()
        assert self.webchat.is_running is True
        await self.webchat.stop()
        assert self.webchat.is_running is False

    @pytest.mark.asyncio
    async def test_create_session(self):
        await self.webchat.start()
        session_id = await self.webchat.create_session(user_name="Marcelo")
        assert session_id is not None

        session = self.webchat.get_session(session_id)
        assert session is not None
        assert session["user_name"] == "Marcelo"

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        await self.webchat.start()
        await self.webchat.create_session(user_name="User1")
        await self.webchat.create_session(user_name="User2")
        sessions = self.webchat.list_sessions()
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_close_session(self):
        await self.webchat.start()
        session_id = await self.webchat.create_session()
        await self.webchat.close_session(session_id)
        assert self.webchat.get_session(session_id) is None

    @pytest.mark.asyncio
    async def test_receive_message_without_handler(self):
        await self.webchat.start()
        session_id = await self.webchat.create_session()
        result = await self.webchat.receive_message(session_id, "Hello")
        # Without handler, returns error message
        assert result is None or "Erro" in (result.text if result else "")

    @pytest.mark.asyncio
    async def test_receive_message_with_handler(self):
        await self.webchat.start()

        async def echo_handler(msg: IncomingMessage) -> OutgoingMessage:
            return OutgoingMessage(text=f"Echo: {msg.text}", chat_id=msg.chat_id)

        self.webchat.set_message_handler(echo_handler)
        session_id = await self.webchat.create_session()
        result = await self.webchat.receive_message(session_id, "Test")
        assert result is not None
        assert result.text == "Echo: Test"

    @pytest.mark.asyncio
    async def test_session_stores_history(self):
        await self.webchat.start()

        async def handler(msg: IncomingMessage) -> OutgoingMessage:
            return OutgoingMessage(text="Ok", chat_id=msg.chat_id)

        self.webchat.set_message_handler(handler)
        session_id = await self.webchat.create_session()
        await self.webchat.receive_message(session_id, "Msg 1")
        await self.webchat.receive_message(session_id, "Msg 2")

        session = self.webchat.get_session(session_id)
        assert len(session["messages"]) == 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_status(self):
        await self.webchat.start()
        status = self.webchat.status()
        assert status["channel"] == "webchat"
        assert status["running"] is True


# ============================================
# Chat Commands Tests
# ============================================
class TestChatCommands:
    def setup_method(self):
        self.handler = ChatCommandHandler()

    def test_is_command(self):
        assert self.handler.is_command("/status") is True
        assert self.handler.is_command("/help") is True
        assert self.handler.is_command("hello") is False
        assert self.handler.is_command("  /agents") is True

    @pytest.mark.asyncio
    async def test_help_command(self):
        msg = IncomingMessage(text="/help")
        result = await self.handler.execute(msg)
        assert result is not None
        assert "Comandos" in result.text
        assert "/status" in result.text

    @pytest.mark.asyncio
    async def test_unknown_command(self):
        msg = IncomingMessage(text="/foobar")
        result = await self.handler.execute(msg)
        assert result is not None
        assert "desconhecido" in result.text

    @pytest.mark.asyncio
    async def test_not_a_command_returns_none(self):
        msg = IncomingMessage(text="just a regular message")
        result = await self.handler.execute(msg)
        assert result is None

    @pytest.mark.asyncio
    async def test_think_command_valid(self):
        msg = IncomingMessage(text="/think deep")
        result = await self.handler.execute(msg)
        assert "deep" in result.text

    @pytest.mark.asyncio
    async def test_think_command_invalid(self):
        msg = IncomingMessage(text="/think ultra")
        result = await self.handler.execute(msg)
        assert "quick" in result.text  # Should show valid options

    @pytest.mark.asyncio
    async def test_compact_command(self):
        msg = IncomingMessage(text="/compact")
        result = await self.handler.execute(msg)
        assert "compactada" in result.text.lower()

    @pytest.mark.asyncio
    async def test_new_command(self):
        msg = IncomingMessage(text="/new")
        result = await self.handler.execute(msg)
        assert "nova" in result.text.lower() or "sessão" in result.text.lower()

    @pytest.mark.asyncio
    async def test_all_commands_defined(self):
        assert len(COMMANDS) >= 8
        assert "/status" in COMMANDS
        assert "/help" in COMMANDS
        assert "/standup" in COMMANDS
