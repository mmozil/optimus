"""
Agent Optimus — Identity: SOUL.md Loader.
Loads and parses SOUL.md files that define agent personality and behavior.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SoulLoader:
    """
    Loads SOUL.md files for agents.

    SOUL.md format:
    ```markdown
    # SOUL.md — AgentName

    **Nome:** AgentName
    **Papel:** Role description
    **Nível:** specialist

    ## Personalidade
    Description of personality traits...

    ## O Que Você Faz
    - Task 1
    - Task 2

    ## O Que Você NÃO Faz
    - Anti-task 1

    ## Formato de Resposta
    - Rule 1
    ```
    """

    _cache: dict[str, str] = {}

    @classmethod
    def load(cls, path: str) -> str:
        """
        Load a SOUL.md file and return its content.
        Caches the result for repeated loads.
        """
        if path in cls._cache:
            return cls._cache[path]

        file_path = Path(path)

        if not file_path.exists():
            logger.warning(f"SOUL.md not found at {path}, using empty soul")
            return ""

        content = file_path.read_text(encoding="utf-8").strip()
        cls._cache[path] = content

        logger.info(f"SOUL.md loaded: {file_path.name} ({len(content)} chars)")
        return content

    @classmethod
    def load_section(cls, path: str, section: str) -> str:
        """Load a specific section from SOUL.md (e.g., 'Personalidade')."""
        content = cls.load(path)
        if not content:
            return ""

        # Find section by heading
        lines = content.split("\n")
        in_section = False
        section_lines = []

        for line in lines:
            if line.strip().startswith("##") and section.lower() in line.lower():
                in_section = True
                continue
            elif line.strip().startswith("##") and in_section:
                break
            elif in_section:
                section_lines.append(line)

        return "\n".join(section_lines).strip()

    @classmethod
    def clear_cache(cls):
        """Clear the SOUL.md cache."""
        cls._cache.clear()

    @classmethod
    def reload(cls, path: str) -> str:
        """Force reload a SOUL.md file."""
        if path in cls._cache:
            del cls._cache[path]
        return cls.load(path)
