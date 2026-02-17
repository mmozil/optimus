"""
Agent Optimus — Session Manager.
Handles conversation persistence in Supabase.
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text

from src.infra.supabase_client import get_async_session

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages user sessions and conversation history.
    Saves and loads messages from the 'conversations' table.
    """

    async def get_or_create_conversation(self, user_id: str, agent_name: str) -> dict:
        """Fetch existing conversation or create a new one."""
        async with get_async_session() as session:
            # Try to find recent conversation for this user and agent
            query = """
                SELECT id, messages, metadata
                FROM conversations
                WHERE user_id = :user_id AND agent_name = :agent_name
                ORDER BY updated_at DESC LIMIT 1
            """
            result = await session.execute(text(query), {"user_id": user_id, "agent_name": agent_name})
            row = result.fetchone()

            if row:
                return {
                    "id": str(row[0]),
                    "messages": row[1] if isinstance(row[1], list) else json.loads(row[1] or "[]"),
                    "metadata": row[2] or {},
                }

            # Create new if not found
            insert_query = """
                INSERT INTO conversations (user_id, agent_name, messages)
                VALUES (:user_id, :agent_name, '[]'::jsonb)
                RETURNING id
            """
            insert_result = await session.execute(text(insert_query), {"user_id": user_id, "agent_name": agent_name})
            new_id = insert_result.fetchone()[0]
            await session.commit()

            return {
                "id": str(new_id),
                "messages": [],
                "metadata": {},
            }

    async def add_message(self, conversation_id: str, role: str, content: str, metadata: dict | None = None):
        """Add a message to a conversation and update DB."""
        async with get_async_session() as session:
            # 1. Fetch current messages
            fetch_query = "SELECT messages FROM conversations WHERE id = :id"
            result = await session.execute(text(fetch_query), {"id": conversation_id})
            row = result.fetchone()

            if not row:
                logger.error(f"Conversation {conversation_id} not found")
                return

            messages = row[0] if isinstance(row[0], list) else json.loads(row[0] or "[]")

            # 2. Append new message
            messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            })

            # 3. Save back
            update_query = """
                UPDATE conversations
                SET messages = :messages, updated_at = now()
                WHERE id = :id
            """
            await session.execute(text(update_query), {"messages": json.dumps(messages), "id": conversation_id})
            await session.commit()

    async def get_history(self, conversation_id: str, limit: int = 10) -> list[dict]:
        """Get the last N messages from a conversation."""
        async with get_async_session() as session:
            query = "SELECT messages FROM conversations WHERE id = :id"
            result = await session.execute(text(query), {"id": conversation_id})
            row = result.fetchone()

            if not row:
                return []

            messages = row[0] if isinstance(row[0], list) else json.loads(row[0] or "[]")
            return messages[-limit:]

# Singleton
session_manager = SessionManager()
