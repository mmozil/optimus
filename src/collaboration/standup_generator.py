"""
Agent Optimus — Standup Generator.
Automatically generates daily standup reports from activity feed and task data.
"""

import logging
from datetime import datetime, timezone

from src.collaboration.activity_feed import ActivityFeed, activity_feed
from src.collaboration.task_manager import TaskManager, TaskStatus, task_manager

logger = logging.getLogger(__name__)


class StandupGenerator:
    """
    Generates daily standup reports for agents and the team.
    Pulls data from activity feed, tasks, and memory.
    """

    def __init__(
        self,
        feed: ActivityFeed | None = None,
        tasks: TaskManager | None = None,
    ):
        self._feed = feed or activity_feed
        self._tasks = tasks or task_manager

    async def generate_agent_standup(self, agent_name: str) -> str:
        """Generate standup for a single agent."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Get activities
        activities = await self._feed.get_by_agent(agent_name, limit=100)
        today_activities = [
            a for a in activities if a.created_at.strftime("%Y-%m-%d") == today
        ]

        # Get tasks
        all_tasks = await self._tasks.list_tasks()

        # Categorize
        completed = [a for a in today_activities if a.type == "task_status_changed"
                     and a.metadata.get("new_status") == "done"]
        in_progress = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
        blocked = [t for t in all_tasks if t.status == TaskStatus.BLOCKED]

        # Build report
        report = f"""## 📋 Standup — {agent_name}
**Data:** {today}

### ✅ O que fiz hoje
"""
        if completed:
            for a in completed:
                report += f"- {a.message}\n"
        elif today_activities:
            report += f"- {len(today_activities)} atividades registradas\n"
        else:
            report += "- Sem atividades registradas hoje\n"

        report += "\n### 🔄 O que estou fazendo\n"
        if in_progress:
            for t in in_progress[:5]:
                report += f"- **{t.title}** ({t.priority.value})\n"
        else:
            report += "- Nenhuma task em andamento\n"

        report += "\n### 🚧 Bloqueios\n"
        if blocked:
            for t in blocked[:5]:
                report += f"- ⚠️ **{t.title}**: {t.description[:100]}\n"
        else:
            report += "- Nenhum bloqueio\n"

        # Stats
        llm_calls = [a for a in today_activities if a.type == "llm_call"]
        total_tokens = sum(a.metadata.get("tokens", 0) for a in llm_calls)

        report += f"""
### 📊 Métricas
- Atividades: **{len(today_activities)}**
- LLM Calls: **{len(llm_calls)}**
- Tokens: **{total_tokens:,}**
"""
        return report

    async def generate_team_standup(self, agent_names: list[str] | None = None) -> str:
        """Generate standup for the entire team."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Get daily summary
        summary = await self._feed.get_daily_summary(today)

        # Team header
        report = f"""# 🤖 Team Standup — Agent Optimus
**Data:** {today}
**Agents Ativos:** {', '.join(summary.get('active_agents', ['nenhum']))}

---

## 📊 Resumo do Time
- **Total de atividades:** {summary['total_activities']}
- **Agents ativos:** {len(summary.get('active_agents', []))}

### Atividades por Tipo
"""
        for activity_type, count in sorted(summary.get("by_type", {}).items()):
            report += f"- `{activity_type}`: {count}\n"

        report += "\n### Atividades por Agent\n"
        for agent, count in sorted(summary.get("by_agent", {}).items()):
            report += f"- **{agent}**: {count}\n"

        # All tasks summary
        all_tasks = await self._tasks.list_tasks()
        status_counts = {}
        for t in all_tasks:
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1

        report += "\n### Status de Tasks\n"
        for status, count in sorted(status_counts.items()):
            emoji = {"inbox": "📥", "assigned": "📌", "in_progress": "🔄",
                     "review": "👀", "done": "✅", "blocked": "🚧"}.get(status, "❓")
            report += f"- {emoji} `{status}`: {count}\n"

        # Individual standups
        agents = agent_names or summary.get("active_agents", [])
        if agents:
            report += "\n---\n"
            for agent in agents:
                agent_standup = await self.generate_agent_standup(agent)
                report += f"\n{agent_standup}\n"

        return report


# Singleton
standup_generator = StandupGenerator()
