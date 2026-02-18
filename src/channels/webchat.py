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

    @property
    def is_running(self) -> bool:
        """Check if channel is active."""
        return self._running

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

    async def receive_message(
        self,
        session_id: str,
        message: str,
        context: dict | None = None,
    ) -> None:
        """
        Process an incoming message from WebChat.
        Called by the FastAPI POST /chat endpoint.

        Spawns a background task that streams response chunks to the session's queue.
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"[WebChat] Unknown session: {session_id}")
            return

        # Store message in session history
        session["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # FASE 0 #16: Spawn background task to stream response via gateway
        asyncio.create_task(self._stream_to_queue(session_id, message, context))

    async def _stream_to_queue(
        self,
        session_id: str,
        message: str,
        context: dict | None = None,
    ):
        """
        Background task: streams gateway response chunks to session queue.

        Call path:
        receive_message() → _stream_to_queue() → gateway.stream_route_message()
        → chunks queued to _response_queues[session_id]
        """
        from src.core.gateway import gateway

        session = self._sessions.get(session_id)
        if not session:
            return

        queue = self._response_queues.get(session_id)
        if not queue:
            return

        try:
            # Stream response from gateway
            async for chunk in gateway.stream_route_message(
                message=message,
                user_id=session["user_id"],
                target_agent=None,
                context=context,
                file_ids=None,
            ):
                await queue.put(chunk)

            # Signal end of stream
            await queue.put({"type": "done"})

        except Exception as e:
            logger.error(f"[WebChat] Streaming failed: {e}")
            await queue.put({"type": "error", "content": str(e)})

    async def stream_responses(self, session_id: str):
        """
        Stream response chunks for a session.

        Yields dict chunks from the session's response queue.
        Chunks are in gateway format: {"type": "token", "content": "..."}

        FASE 0 #16: Integrates with gateway.stream_route_message() output.
        """
        queue = self._response_queues.get(session_id)
        if not queue:
            yield {"type": "error", "content": "session_not_found"}
            return

        while self._running:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=30.0)

                yield chunk

                # Stop streaming on done/error
                if chunk.get("type") in ("done", "error"):
                    break

            except asyncio.TimeoutError:
                # Send keepalive
                yield {"type": "keepalive"}

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


# Singleton
webchat_channel = WebChatChannel()
