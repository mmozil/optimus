"""
Agent Optimus — WebChat Channel Adapter.
REST API + SSE streaming for web-based chat interface.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from src.channels.base_channel import (
    BaseChannel, ChannelType, IncomingMessage, OutgoingMessage,
)

logger = logging.getLogger(__name__)


class WebChatChannel(BaseChannel):
    """
    WebChat channel — REST API based.
    Uses SSE (Server-Sent Events) for real-time streaming.
    Integrates directly with FastAPI endpoints.
    """

    def __init__(self, config: dict | None = None):
        super().__init__(ChannelType.WEBCHAT, config)
        self._sessions: dict[str, dict] = {}  # session_id → session data
        self._response_queues: dict[str, asyncio.Queue] = {}  # session_id → response queue

    async def start(self):
        """Mark WebChat as active (no external connection needed)."""
        self._running = True
        logger.info("[WebChat] Channel active")

    async def stop(self):
        """Stop WebChat channel."""
        self._running = False
        self._sessions.clear()
        self._response_queues.clear()
        logger.info("[WebChat] Channel stopped")

    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message to a WebChat session (pushes to SSE queue)."""
        session_id = message.chat_id
        queue = self._response_queues.get(session_id)

        if queue:
            await queue.put(message)
            return True

        logger.warning(f"[WebChat] No active session: {session_id}")
        return False

    # ============================================
    # Session Management
    # ============================================

    async def create_session(self, user_id: str = "", user_name: str = "") -> str:
        """Create a new chat session. Returns session_id."""
        session_id = str(uuid4())
        self._sessions[session_id] = {
            "id": session_id,
            "user_id": user_id or session_id,
            "user_name": user_name or "User",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }
        self._response_queues[session_id] = asyncio.Queue()

        logger.info(f"[WebChat] Session created: {session_id}")
        return session_id

    async def close_session(self, session_id: str):
        """Close a chat session."""
        self._sessions.pop(session_id, None)
        self._response_queues.pop(session_id, None)
        logger.info(f"[WebChat] Session closed: {session_id}")

    async def receive_message(self, session_id: str, text: str) -> OutgoingMessage | None:
        """
        Process an incoming message from WebChat.
        Called by the FastAPI POST /chat endpoint.
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"[WebChat] Unknown session: {session_id}")
            return None

        incoming = IncomingMessage(
            channel=ChannelType.WEBCHAT,
            chat_id=session_id,
            user_id=session["user_id"],
            user_name=session["user_name"],
            text=text,
        )

        # Store in session history
        session["messages"].append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Process through handler
        response = await self.handle_incoming(incoming)

        if response:
            session["messages"].append({
                "role": "assistant",
                "content": response.text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return response

    async def stream_responses(self, session_id: str):
        """
        SSE generator for streaming responses.
        Use with FastAPI StreamingResponse.

        Example FastAPI endpoint:
            @app.get("/chat/{session_id}/stream")
            async def stream(session_id: str):
                return StreamingResponse(
                    webchat.stream_responses(session_id),
                    media_type="text/event-stream"
                )
        """
        queue = self._response_queues.get(session_id)
        if not queue:
            yield "data: {\"error\": \"session_not_found\"}\n\n"
            return

        while self._running:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {{\"text\": \"{message.text}\", \"chat_id\": \"{message.chat_id}\"}}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive
                yield ": keepalive\n\n"

    def get_session(self, session_id: str) -> dict | None:
        """Get session data."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict]:
        """List all active sessions."""
        return [
            {
                "id": s["id"],
                "user_name": s["user_name"],
                "messages": len(s["messages"]),
                "created_at": s["created_at"],
            }
            for s in self._sessions.values()
        ]
