"""
Agent Optimus — Planning Engine (Phase 15).
Decomposes complex tasks into executable steps before running them.
Enables "show your work" — the agent explains its plan before acting.
"""

import json
import logging
from dataclasses import dataclass, field

from src.core.config import settings

logger = logging.getLogger(__name__)


# ============================================
# Data Models
# ============================================

@dataclass
class PlanStep:
    """A single step in an execution plan."""
    index: int
    description: str
    agent: str = "optimus"          # Which agent will execute
    tool: str = ""                  # Specific tool to use, if known
    depends_on: list[int] = field(default_factory=list)
    status: str = "pending"         # pending | running | done | failed | skipped
    result: str = ""
    error: str = ""


@dataclass
class ExecutionPlan:
    """A complete plan for executing a complex task."""
    task: str                        # Original user request
    reasoning: str                   # Why the agent chose this plan
    steps: list[PlanStep] = field(default_factory=list)
    approved: bool = False           # User must approve before execution
    status: str = "draft"            # draft | approved | executing | completed | failed


PLANNING_SYSTEM_PROMPT = """Você é um planejador de tarefas. Analise a solicitação do usuário e decomponha-a em passos executáveis.

REGRAS:
1. Cada passo deve ser atômico e claro
2. Identifique qual agente (optimus, friday, fury) é o melhor para cada passo
3. Identifique dependências entre os passos
4. Seja conciso — máximo 7 passos para qualquer tarefa

Responda EXCLUSIVAMENTE em JSON válido, sem blocos de código, sem markdown:
{
    "reasoning": "Explicação breve do por quê essa abordagem",
    "steps": [
        {
            "index": 1,
            "description": "O que este passo faz",
            "agent": "nome_do_agente",
            "tool": "nome_da_tool_se_aplicável",
            "depends_on": []
        }
    ]
}
"""


class PlanningEngine:
    """
    Decomposes complex tasks into plans with multiple steps.
    The plan is shown to the user for approval before execution.
    """

    def __init__(self):
        self._complexity_threshold = 50  # Chars — heuristic for "complex" tasks

    async def should_plan(self, message: str, context: dict | None = None) -> bool:
        """
        Heuristic: decide if a task is complex enough to warrant planning.
        Simple questions or single-action requests skip planning.
        """
        # Short messages are usually simple questions
        if len(message) < self._complexity_threshold:
            return False

        # Multi-step keywords (PT-BR and EN)
        planning_keywords = [
            "passo a passo", "etapas", "plano", "implementar", "construir",
            "criar sistema", "migrar", "refatorar", "deploy", "configurar",
            "step by step", "implement", "build", "migrate", "refactor",
            "analise completa", "full analysis", "end to end",
        ]

        message_lower = message.lower()
        return any(kw in message_lower for kw in planning_keywords)

    async def create_plan(self, message: str, context: dict | None = None) -> ExecutionPlan:
        """
        Use the LLM to decompose a task into an execution plan.
        Returns a plan for user approval — does NOT execute anything.
        """
        from src.infra.model_router import model_router

        messages = [
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]

        result = await model_router.generate_with_history(
            messages=messages,
            chain="default",
            temperature=0.3,
            max_tokens=2048,
        )

        raw = result.get("content", "")

        # Parse the JSON response
        try:
            # Handle markdown code blocks if the LLM wraps in ```json
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]  # Remove first line
                cleaned = cleaned.rsplit("```", 1)[0]  # Remove last ```
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(f"Planning LLM returned non-JSON: {raw[:200]}")
            # Fallback: single-step plan
            return ExecutionPlan(
                task=message,
                reasoning="Não foi possível decompor a tarefa. Executando diretamente.",
                steps=[PlanStep(index=1, description=message, agent="optimus")],
                status="draft",
            )

        steps = [
            PlanStep(
                index=s.get("index", i + 1),
                description=s.get("description", ""),
                agent=s.get("agent", "optimus"),
                tool=s.get("tool", ""),
                depends_on=s.get("depends_on", []),
            )
            for i, s in enumerate(data.get("steps", []))
        ]

        plan = ExecutionPlan(
            task=message,
            reasoning=data.get("reasoning", ""),
            steps=steps,
            status="draft",
        )

        logger.info(f"Plan created with {len(steps)} steps for: {message[:80]}")
        return plan

    async def execute_plan(self, plan: ExecutionPlan, context: dict | None = None) -> ExecutionPlan:
        """
        Execute an approved plan step by step.
        Each step is processed by the designated agent.
        """
        if not plan.approved:
            raise ValueError("O plano precisa ser aprovado antes da execução.")

        from src.core.agent_factory import AgentFactory

        plan.status = "executing"

        for step in plan.steps:
            # Check dependencies
            unfinished_deps = [
                d for d in step.depends_on
                if any(s.index == d and s.status != "done" for s in plan.steps)
            ]
            if unfinished_deps:
                step.status = "skipped"
                step.error = f"Dependências não concluídas: {unfinished_deps}"
                continue

            step.status = "running"
            logger.info(f"Executing step {step.index}: {step.description[:60]}")

            try:
                agent = AgentFactory.get(step.agent)
                if not agent:
                    agent = AgentFactory.get("optimus")

                result = await agent.process(step.description, context or {})
                step.result = result.get("content", "")
                step.status = "done"

            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                logger.error(f"Step {step.index} failed: {e}")

        # Determine overall status
        all_done = all(s.status == "done" for s in plan.steps)
        plan.status = "completed" if all_done else "failed"

        return plan

    def format_plan_for_user(self, plan: ExecutionPlan) -> str:
        """Format a plan as a readable message for user approval."""
        lines = [
            f"📋 **Plano de Execução**\n",
            f"**Tarefa:** {plan.task}\n",
            f"**Raciocínio:** {plan.reasoning}\n",
            f"**Passos ({len(plan.steps)}):**\n",
        ]

        for step in plan.steps:
            deps = f" (após passo {step.depends_on})" if step.depends_on else ""
            agent_label = f" → `{step.agent}`" if step.agent != "optimus" else ""
            lines.append(f"{step.index}. {step.description}{agent_label}{deps}")

        lines.append("\n✅ Para aprovar, responda com **'aprovar'** ou **'executar'**.")
        lines.append("❌ Para ajustar, descreva as mudanças desejadas.")

        return "\n".join(lines)

    def format_plan_result(self, plan: ExecutionPlan) -> str:
        """Format completed plan results for the user."""
        lines = [f"📋 **Resultado do Plano** ({plan.status})\n"]

        for step in plan.steps:
            icon = "✅" if step.status == "done" else "❌" if step.status == "failed" else "⏭"
            lines.append(f"{icon} **Passo {step.index}:** {step.description}")
            if step.result:
                # Truncate long results
                preview = step.result[:200] + "..." if len(step.result) > 200 else step.result
                lines.append(f"   → {preview}")
            if step.error:
                lines.append(f"   ⚠️ Erro: {step.error}")

        return "\n".join(lines)


# Singleton
planning_engine = PlanningEngine()
