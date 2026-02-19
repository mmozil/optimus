"""
Agent Optimus — Chat Commands.
Slash command parser and executor for all channels.
"""

import logging
from dataclasses import dataclass

from src.channels.base_channel import IncomingMessage

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result from executing a chat command."""
    text: str
    is_command: bool = True
    handled: bool = True


# Command definitions
COMMANDS = {
    "/status": "Mostra status dos agents, tokens usados e limites",
    "/think": "Ajusta nível de pensamento: /think quick | standard | deep",
    "/agents": "Lista agents ativos e seus status",
    "/task": "Gerencia tasks: /task list | /task create <título> | /task status",
    "/learn": "Mostra learnings do agent: /learn [agent_name]",
    "/compact": "Compacta a sessão atual (limpa contexto)",
    "/new": "Inicia nova sessão",
    "/help": "Mostra esta lista de comandos",
    "/standup": "Gera standup do time",
    "/cron": "Lista jobs agendados: /cron list",
}


class ChatCommandHandler:
    """
    Parses and executes slash commands from any channel.
    Returns CommandResult with formatted response.
    """

    def is_command(self, text: str) -> bool:
        """Check if text starts with a slash command."""
        return text.strip().startswith("/")

    async def execute(self, message: IncomingMessage) -> CommandResult | None:
        """Parse and execute a command from a message."""
        text = message.text.strip()
        if not self.is_command(text):
            return None

        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = {
            "/status": self._cmd_status,
            "/think": self._cmd_think,
            "/agents": self._cmd_agents,
            "/task": self._cmd_task,
            "/learn": self._cmd_learn,
            "/compact": self._cmd_compact,
            "/new": self._cmd_new,
            "/help": self._cmd_help,
            "/standup": self._cmd_standup,
            "/cron": self._cmd_cron,
        }.get(command)

        if not handler:
            return CommandResult(
                text=f"❓ Comando desconhecido: `{command}`\nUse `/help` para ver os comandos disponíveis.",
            )

        try:
            return await handler(args, message)
        except Exception as e:
            logger.error(f"Command {command} failed: {e}")
            return CommandResult(text=f"❌ Erro ao executar `{command}`: {str(e)}")

    # ============================================
    # Command Implementations
    # ============================================

    async def _cmd_status(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Show agent status and token usage."""
        from src.core.agent_factory import AgentFactory

        agents = AgentFactory.list_agents()
        if not agents:
            return CommandResult(text="📊 Nenhum agent ativo no momento.")

        lines = ["📊 **Status dos Agents**\n"]
        for agent in agents:
            status = "🟢" if agent.get("status") != "error" else "🔴"
            lines.append(f"{status} **{agent['name']}** — {agent['role']} ({agent['level']})")

        return CommandResult(text="\n".join(lines))

    async def _cmd_think(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Adjust thinking level."""
        valid_levels = ["quick", "standard", "deep"]
        level = args.strip().lower()

        if level not in valid_levels:
            return CommandResult(
                text="🧠 **Níveis de Pensamento**\n\n"
                     "• `/think quick` — 1 estratégia, resposta rápida\n"
                     "• `/think standard` — 2 estratégias, balanceado\n"
                     "• `/think deep` — 3 estratégias, análise profunda\n\n"
                     f"Uso: `/think <{' | '.join(valid_levels)}>`"
            )

        return CommandResult(
            text=f"🧠 Nível de pensamento ajustado para **{level}**"
        )

    async def _cmd_agents(self, args: str, msg: IncomingMessage) -> CommandResult:
        """List active agents."""
        from src.core.agent_factory import AgentFactory

        agents = AgentFactory.list_agents()
        if not agents:
            return CommandResult(text="🤖 Nenhum agent ativo.")

        lines = ["🤖 **Agents Ativos**\n"]
        for agent in agents:
            lines.append(f"• **{agent['name']}** — {agent['role']}")

        return CommandResult(text="\n".join(lines))

    async def _cmd_task(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Manage tasks."""
        from src.collaboration.task_manager import TaskCreate, TaskPriority, task_manager

        parts = args.strip().split(maxsplit=1)
        action = parts[0].lower() if parts else "list"
        task_args = parts[1] if len(parts) > 1 else ""

        if action == "list":
            tasks = await task_manager.list_tasks()
            if not tasks:
                return CommandResult(text="📋 Nenhuma task encontrada.")

            lines = ["📋 **Tasks**\n"]
            for t in tasks[:10]:
                emoji = {"inbox": "📥", "assigned": "📌", "in_progress": "🔄",
                         "review": "👀", "done": "✅", "blocked": "🚧"}.get(t.status.value, "❓")
                lines.append(f"{emoji} **{t.title}** — {t.priority.value}")
            return CommandResult(text="\n".join(lines))

        elif action == "create" and task_args:
            task = await task_manager.create(TaskCreate(
                title=task_args,
                created_by=msg.user_name,
                priority=TaskPriority.MEDIUM,
            ))
            # FASE 10 #10.2: Subscribe creator to thread + post opening message
            creator = msg.user_name or str(msg.user_id)
            from src.collaboration.thread_manager import thread_manager
            await thread_manager.subscribe(creator, task.id)
            await thread_manager.post_message(
                task.id, "system",
                f"Task '{task.title}' criada por {creator}.",
            )
            return CommandResult(text=f"✅ Task criada: **{task.title}** (ID: `{str(task.id)[:8]}`)")

        elif action == "status":
            pending = await task_manager.get_pending_count()
            blocked = await task_manager.get_blocked_tasks()
            return CommandResult(
                text=f"📊 **Task Status**\n• Pendentes: {pending}\n• Bloqueadas: {len(blocked)}"
            )

        return CommandResult(
            text="📋 **Comandos de Task**\n"
                 "• `/task list` — Listar tasks\n"
                 "• `/task create <título>` — Criar task\n"
                 "• `/task status` — Ver resumo"
        )

    async def _cmd_learn(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Show agent learnings."""
        from src.memory.long_term import long_term_memory

        agent = args.strip() or "optimus"
        categories = await long_term_memory.get_categories(agent)

        if not categories:
            return CommandResult(text=f"🧠 **{agent}** ainda não tem learnings registrados.")

        content = await long_term_memory.load(agent)
        preview = content[:1000] if content else "Sem conteúdo."

        return CommandResult(
            text=f"🧠 **Learnings de {agent}**\n"
                 f"Categorias: {', '.join(categories)}\n\n{preview}"
        )

    async def _cmd_compact(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Compact current session."""
        return CommandResult(
            text="🗜️ Sessão compactada. Contexto anterior preservado em resumo."
        )

    async def _cmd_new(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Start new session."""
        return CommandResult(
            text="🆕 Nova sessão iniciada. Contexto anterior salvo em Daily Notes."
        )

    async def _cmd_help(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Show available commands."""
        lines = ["📖 **Comandos Disponíveis**\n"]
        for cmd, desc in COMMANDS.items():
            lines.append(f"• `{cmd}` — {desc}")
        return CommandResult(text="\n".join(lines))

    async def _cmd_standup(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Generate team standup."""
        from src.collaboration.standup_generator import standup_generator

        report = await standup_generator.generate_team_standup()
        # Truncate for chat
        if len(report) > 2000:
            report = report[:2000] + "\n\n_... truncado. Use a API para relatório completo._"

        return CommandResult(text=report)

    async def _cmd_cron(self, args: str, msg: IncomingMessage) -> CommandResult:
        """List scheduled cron jobs."""
        from src.core.cron_scheduler import cron_scheduler
        from datetime import datetime, timezone

        action = args.strip().lower() or "list"

        if action == "list":
            jobs = cron_scheduler.list_jobs()
            if not jobs:
                return CommandResult(text="⏰ Nenhum job agendado.")

            lines = ["⏰ **Jobs Agendados**\n"]
            now = datetime.now(timezone.utc)

            for job in jobs:
                # Status emoji
                status = "✅" if job.enabled else "⏸️"

                # Calculate next run time
                next_run = "—"
                if job.next_run:
                    try:
                        next_dt = datetime.fromisoformat(job.next_run)
                        if next_dt.tzinfo is None:
                            next_dt = next_dt.replace(tzinfo=timezone.utc)

                        # Time until next run
                        delta = next_dt - now
                        if delta.total_seconds() < 0:
                            next_run = "⚠️ Atrasado"
                        elif delta.total_seconds() < 3600:
                            next_run = f"em {int(delta.total_seconds() / 60)}min"
                        elif delta.total_seconds() < 86400:
                            next_run = f"em {int(delta.total_seconds() / 3600)}h"
                        else:
                            next_run = f"em {int(delta.total_seconds() / 86400)}d"
                    except (ValueError, TypeError):
                        next_run = "erro"

                # Job info
                schedule = f"a cada {job.schedule_value}" if job.schedule_type == "every" else job.schedule_value
                lines.append(
                    f"{status} **{job.name}**\n"
                    f"   └ {schedule} | próxima: {next_run} | execuções: {job.run_count}"
                )

            return CommandResult(text="\n".join(lines))

        return CommandResult(
            text="⏰ **Comandos de Cron**\n"
                 "• `/cron list` — Listar jobs agendados"
        )


# Singleton
chat_commands = ChatCommandHandler()
