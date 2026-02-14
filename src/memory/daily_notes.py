"""
Agent Optimus — Daily Notes.
Automatic daily activity log per agent. Stored as markdown files by date.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DAILY_DIR = Path(__file__).parent.parent.parent / "workspace" / "memory" / "daily"


class DailyNotes:
    """
    Manages daily activity notes per agent.
    Each day gets a separate markdown file: YYYY-MM-DD.md
    """

    def __init__(self, daily_dir: Path | None = None):
        self.daily_dir = daily_dir or DAILY_DIR
        self.daily_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, agent_name: str, date: str | None = None) -> Path:
        date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        agent_dir = self.daily_dir / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir / f"{date}.md"

    async def log(self, agent_name: str, event_type: str, message: str, metadata: dict | None = None):
        """
        Log an activity to today's daily note.

        Args:
            agent_name: Name of the agent
            event_type: Type of event (task_started, message_sent, llm_call, etc.)
            message: Human-readable description
            metadata: Optional structured data
        """
        path = self._file_path(agent_name)
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Create file with header if new
        if not path.exists():
            header = f"# Daily Notes — {agent_name}\n**Data:** {today}\n\n---\n\n"
            path.write_text(header, encoding="utf-8")

        # Append entry
        entry = f"### [{timestamp}] {event_type}\n{message}\n"
        if metadata:
            meta_str = " | ".join(f"`{k}`: {v}" for k, v in metadata.items())
            entry += f"_{meta_str}_\n"
        entry += "\n"

        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)

        logger.debug(f"Daily note logged: {agent_name}/{event_type}")

    async def get_today(self, agent_name: str) -> str:
        """Get today's daily notes for an agent."""
        path = self._file_path(agent_name)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"# Daily Notes — {agent_name}\nSem atividades hoje."

    async def get_date(self, agent_name: str, date: str) -> str:
        """Get daily notes for a specific date (YYYY-MM-DD)."""
        path = self._file_path(agent_name, date)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"# Daily Notes — {agent_name}\nSem atividades em {date}."

    async def get_summary(self, agent_name: str, days: int = 7) -> list[dict]:
        """Get summary of recent daily notes."""
        agent_dir = self.daily_dir / agent_name
        if not agent_dir.exists():
            return []

        files = sorted(agent_dir.glob("*.md"), reverse=True)[:days]
        summaries = []

        for f in files:
            content = f.read_text(encoding="utf-8")
            entry_count = content.count("### [")
            summaries.append({
                "date": f.stem,
                "entries": entry_count,
                "size": len(content),
            })

        return summaries


# Singleton
daily_notes = DailyNotes()
