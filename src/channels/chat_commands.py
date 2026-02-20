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
    "/status":   "Mostra status dos agents, tokens usados e limites",
    "/think":    "Ajusta nível de pensamento: /think quick | standard | deep",
    "/agents":   "Lista agents ativos e seus status",
    "/task":     "Gerencia tasks: /task list | /task create <título> | /task status",
    "/learn":    "Mostra learnings do agent: /learn [agent_name]",
    "/memory":   "Exibe memória de longo prazo do agente sobre você",
    "/tools":    "Lista todas as tools MCP disponíveis",
    "/activity": "Feed de atividades recentes (tasks, crons, eventos)",
    "/compact":  "Compacta a sessão atual (limpa contexto)",
    "/clear":    "Limpa o chat na tela (contexto preservado)",
    "/new":      "Inicia nova sessão",
    "/standup":  "Gera standup do time",
    "/cron":     "Jobs agendados: /cron list | /cron enable <nome> | /cron disable <nome>",
    "/help":     "Mostra esta lista de comandos",
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
            "/status":   self._cmd_status,
            "/think":    self._cmd_think,
            "/agents":   self._cmd_agents,
            "/task":     self._cmd_task,
            "/learn":    self._cmd_learn,
            "/memory":   self._cmd_memory,
            "/tools":    self._cmd_tools,
            "/activity": self._cmd_activity,
            "/compact":  self._cmd_compact,
            "/clear":    self._cmd_clear,
            "/new":      self._cmd_new,
            "/help":     self._cmd_help,
            "/standup":  self._cmd_standup,
            "/cron":     self._cmd_cron,
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

        cron_parts = args.strip().split(maxsplit=1)
        action = cron_parts[0].lower() if cron_parts else "list"
        action_args = cron_parts[1] if len(cron_parts) > 1 else ""

        if action == "list":
            jobs = cron_scheduler.list_jobs()
            if not jobs:
                return CommandResult(text="⏰ Nenhum job agendado.")

            lines = ["⏰ **Jobs Agendados**\n"]
            now = datetime.now(timezone.utc)

            for job in jobs:
                status = "✅" if job.enabled else "⏸️"
                next_run = "—"
                if job.next_run:
                    try:
                        next_dt = datetime.fromisoformat(job.next_run)
                        if next_dt.tzinfo is None:
                            next_dt = next_dt.replace(tzinfo=timezone.utc)
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
                schedule = f"a cada {job.schedule_value}" if job.schedule_type == "every" else job.schedule_value
                lines.append(
                    f"{status} **{job.name}**\n"
                    f"   └ {schedule} | próxima: {next_run} | execuções: {job.run_count}"
                )

            return CommandResult(text="\n".join(lines))

        if action in ("enable", "disable") and action_args:
            jobs = cron_scheduler.list_jobs()
            name_lower = action_args.lower()
            matched = [j for j in jobs if name_lower in j.name.lower()]

            if not matched:
                return CommandResult(
                    text=f"⏰ Nenhum job encontrado com o nome `{action_args}`.\n"
                         "Use `/cron list` para ver os nomes disponíveis."
                )

            results = []
            for job in matched:
                job.enabled = (action == "enable")
                cron_scheduler._save()
                state = "ativado ✅" if job.enabled else "pausado ⏸️"
                results.append(f"**{job.name}** {state}")

            return CommandResult(text="⏰ " + "\n".join(results))

        return CommandResult(
            text="⏰ **Comandos de Cron**\n"
                 "• `/cron list` — Listar jobs agendados\n"
                 "• `/cron enable <nome>` — Ativar job\n"
                 "• `/cron disable <nome>` — Pausar job"
        )

    async def _cmd_memory(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Show agent long-term memory about the user."""
        from src.memory.long_term import long_term_memory

        agent = args.strip() or "optimus"
        content = await long_term_memory.load(agent)

        if not content or not content.strip():
            return CommandResult(
                text=f"🧠 **Memória de longo prazo** (`{agent}`)\n\nNenhum dado salvo ainda."
            )

        # Truncate for chat display
        preview = content.strip()
        truncated = ""
        if len(preview) > 2000:
            preview = preview[:2000]
            truncated = "\n\n_... truncado. Memória completa disponível internamente._"

        return CommandResult(
            text=f"🧠 **Memória de longo prazo** (`{agent}`)\n\n{preview}{truncated}"
        )

    async def _cmd_tools(self, args: str, msg: IncomingMessage) -> CommandResult:
        """List all available MCP tools."""
        from src.skills.mcp_tools import mcp_tools

        category_filter = args.strip().lower() or None
        tools = mcp_tools.list_tools(category=category_filter)

        if not tools:
            hint = f" na categoria `{category_filter}`" if category_filter else ""
            return CommandResult(text=f"🔧 Nenhuma tool encontrada{hint}.")

        # Group by category
        by_category: dict[str, list] = {}
        for t in sorted(tools, key=lambda x: (x.category, x.name)):
            by_category.setdefault(t.category, []).append(t)

        lines = [f"🔧 **Tools MCP disponíveis** ({len(tools)} total)\n"]
        for cat, cat_tools in by_category.items():
            lines.append(f"**{cat.upper()}**")
            for t in cat_tools:
                approval = " ⚠️" if t.requires_approval else ""
                lines.append(f"• `{t.name}`{approval} — {t.description[:60]}")
            lines.append("")

        if category_filter is None:
            lines.append("_Use `/tools <categoria>` para filtrar._")

        return CommandResult(text="\n".join(lines))

    async def _cmd_activity(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Show recent activity feed."""
        from src.collaboration.activity_feed import activity_feed

        limit = 10
        try:
            limit = int(args.strip()) if args.strip() else 10
        except ValueError:
            pass
        limit = min(limit, 30)

        activities = await activity_feed.get_recent(limit=limit)

        if not activities:
            return CommandResult(text="📡 Nenhuma atividade registrada ainda.")

        type_emoji = {
            "task_created": "📋",
            "task_status_changed": "🔄",
            "task_completed": "✅",
            "message_sent": "💬",
            "cron_triggered": "⏰",
            "standup_generated": "📊",
            "agent_started": "🤖",
        }

        lines = [f"📡 **Atividade Recente** (últimas {len(activities)})\n"]
        for a in activities:
            emoji = type_emoji.get(a.type, "•")
            ts = a.created_at.strftime("%d/%m %H:%M")
            agent = f" _[{a.agent_name}]_" if a.agent_name else ""
            lines.append(f"{emoji} `{ts}`{agent} {a.message[:80]}")

        return CommandResult(text="\n".join(lines))

    async def _cmd_clear(self, args: str, msg: IncomingMessage) -> CommandResult:
        """Clear the chat screen (frontend-handled)."""
        # The frontend intercepts /clear before sending to API.
        # This handler exists as fallback for non-web channels.
        return CommandResult(
            text="🧹 Chat limpo. Contexto da sessão preservado.",
            is_command=True,
            handled=True,
        )


# Singleton
chat_commands = ChatCommandHandler()
