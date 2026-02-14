"""
Agent Optimus — Skills Registry.
Catalogue, install/uninstall, and manage agent skills dynamically.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """A registered skill definition."""
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"  # general, code, research, analysis, creative, security
    agent_compatibility: list[str] = field(default_factory=lambda: ["all"])
    tools: list[str] = field(default_factory=list)
    mcp_server: str | None = None  # Associated MCP server module
    enabled: bool = True
    installed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    skill_md_path: str | None = None  # Path to SKILL.md


class SkillsRegistry:
    """
    Manages the catalogue of available agent skills.
    Supports dynamic install/uninstall and SKILL.md documentation.
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._register_builtin_skills()

    def install(self, skill: Skill) -> bool:
        """Install a new skill."""
        if skill.name in self._skills:
            logger.warning(f"Skill '{skill.name}' already installed, updating")

        self._skills[skill.name] = skill
        logger.info(f"Skill installed: {skill.name} v{skill.version}")
        return True

    def uninstall(self, name: str) -> bool:
        """Uninstall a skill."""
        if name in self._skills:
            del self._skills[name]
            logger.info(f"Skill uninstalled: {name}")
            return True
        return False

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_skills(
        self,
        category: str | None = None,
        agent: str | None = None,
        enabled_only: bool = True,
    ) -> list[Skill]:
        """List skills with optional filters."""
        skills = list(self._skills.values())

        if enabled_only:
            skills = [s for s in skills if s.enabled]
        if category:
            skills = [s for s in skills if s.category == category]
        if agent:
            skills = [s for s in skills if "all" in s.agent_compatibility or agent in s.agent_compatibility]

        return sorted(skills, key=lambda s: s.name)

    def enable(self, name: str) -> bool:
        """Enable a disabled skill."""
        if name in self._skills:
            self._skills[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a skill without uninstalling."""
        if name in self._skills:
            self._skills[name].enabled = False
            return True
        return False

    def get_categories(self) -> list[str]:
        """Get all skill categories."""
        return sorted(set(s.category for s in self._skills.values()))

    def generate_catalogue(self) -> str:
        """Generate SKILLS.md catalogue."""
        lines = ["# 🎯 Skills Catalogue\n", "_Agent Optimus — Available Skills_\n"]

        categories = self.get_categories()
        for category in categories:
            skills = self.list_skills(category=category, enabled_only=False)
            lines.append(f"\n## {category.upper()}\n")

            for skill in skills:
                status = "✅" if skill.enabled else "⏸️"
                agents = ", ".join(skill.agent_compatibility)
                lines.append(f"### {status} {skill.name} (v{skill.version})")
                lines.append(f"{skill.description}")
                lines.append(f"_Agents: {agents}_\n")

                if skill.tools:
                    lines.append(f"**Tools:** {', '.join(skill.tools)}")
                    lines.append("")

        return "\n".join(lines)

    async def load_from_directory(self, skills_dir: str) -> int:
        """Auto-discover and install skills from SKILL.md files."""
        path = Path(skills_dir)
        if not path.exists():
            return 0

        loaded = 0
        for skill_md in path.rglob("SKILL.md"):
            try:
                content = skill_md.read_text(encoding="utf-8")
                skill = self._parse_skill_md(content, str(skill_md))
                if skill:
                    self.install(skill)
                    loaded += 1
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_md}: {e}")

        return loaded

    def _parse_skill_md(self, content: str, path: str) -> Skill | None:
        """Parse a SKILL.md file into a Skill object."""
        lines = content.strip().split("\n")
        if not lines:
            return None

        name = lines[0].lstrip("# ").strip()
        description = ""
        category = "general"

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("Description:"):
                description = line.split(":", 1)[1].strip()
            elif line.startswith("Category:"):
                category = line.split(":", 1)[1].strip()
            elif not description and line and not line.startswith("#"):
                description = line

        return Skill(
            name=name,
            description=description or name,
            category=category,
            skill_md_path=path,
        )

    # ============================================
    # Built-in Skills
    # ============================================

    def _register_builtin_skills(self):
        """Register built-in skills."""
        builtins = [
            Skill(
                name="code_generation",
                description="Geração de código em múltiplas linguagens",
                category="code",
                agent_compatibility=["friday", "all"],
                tools=["fs_read", "fs_write", "db_query"],
            ),
            Skill(
                name="code_review",
                description="Análise e review de código com sugestões",
                category="code",
                agent_compatibility=["friday", "guardian", "all"],
                tools=["fs_read"],
            ),
            Skill(
                name="web_research",
                description="Pesquisa web e síntese de informações",
                category="research",
                agent_compatibility=["fury", "all"],
                tools=["research_search", "research_fetch_url"],
            ),
            Skill(
                name="data_analysis",
                description="Análise de dados e geração de insights",
                category="analysis",
                agent_compatibility=["analyst", "all"],
                tools=["db_query", "memory_search"],
            ),
            Skill(
                name="content_writing",
                description="Redação de conteúdo, copy e documentação",
                category="creative",
                agent_compatibility=["writer", "all"],
                tools=["fs_write"],
            ),
            Skill(
                name="security_audit",
                description="Auditoria de segurança e compliance",
                category="security",
                agent_compatibility=["guardian", "all"],
                tools=["fs_read", "db_query"],
            ),
            Skill(
                name="task_management",
                description="Criação e gerenciamento de tasks",
                category="general",
                agent_compatibility=["all"],
                tools=["memory_search", "memory_learn"],
            ),
            Skill(
                name="deep_thinking",
                description="Análise profunda com Tree-of-Thought",
                category="analysis",
                agent_compatibility=["optimus", "all"],
                tools=["memory_search"],
            ),
        ]

        for skill in builtins:
            self.install(skill)


# Singleton
skills_registry = SkillsRegistry()
