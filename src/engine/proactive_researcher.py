"""
Agent Optimus — Proactive Researcher (Fase 11: Jarvis Mode).
When idle, proactively monitors configurable sources (RSS, GitHub, URLs)
for topics of interest and generates briefings. Rate-limited by source.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

RESEARCH_DIR = Path(__file__).parent.parent.parent / "workspace" / "research"
SOURCES_FILE = RESEARCH_DIR / "sources.json"
FINDINGS_DIR = RESEARCH_DIR / "findings"


@dataclass
class ResearchSource:
    """A monitored information source."""

    name: str
    type: str = "url"  # "rss", "github", "url", "api"
    url: str = ""
    check_interval: str = "24h"  # How often to check: "1h", "6h", "24h", "7d"
    last_checked: str = ""
    enabled: bool = True
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchSource":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ResearchFinding:
    """A piece of information discovered from a source."""

    title: str
    summary: str
    source_name: str
    url: str = ""
    relevance: float = 0.5  # 0.0 to 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class ProactiveResearcher:
    """
    Monitors external sources for new information relevant to the user.

    Features:
    - Configurable sources (RSS, GitHub, URLs)
    - Rate limiting per source (respects check_interval)
    - Generates markdown briefings from findings
    - Persistent source config in JSON
    """

    def __init__(self):
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
        self._sources: dict[str, ResearchSource] = {}
        self._load()

    def _load(self) -> None:
        """Load sources from persistent storage."""
        if SOURCES_FILE.exists():
            try:
                data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
                for src_data in data:
                    src = ResearchSource.from_dict(src_data)
                    self._sources[src.name] = src
                logger.info(f"Research: loaded {len(self._sources)} sources")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Research: failed to load sources: {e}")

    def _save(self) -> None:
        """Persist sources to JSON."""
        data = [src.to_dict() for src in self._sources.values()]
        SOURCES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_source(self, source: ResearchSource) -> None:
        """Add a new research source."""
        self._sources[source.name] = source
        self._save()
        logger.info(f"Research: source '{source.name}' added ({source.type}: {source.url})")

    def remove_source(self, name: str) -> bool:
        """Remove a research source."""
        if name in self._sources:
            del self._sources[name]
            self._save()
            logger.info(f"Research: source '{name}' removed")
            return True
        return False

    def list_sources(self, enabled_only: bool = False) -> list[ResearchSource]:
        """List all configured sources."""
        sources = list(self._sources.values())
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        return sources

    def get_source(self, name: str) -> ResearchSource | None:
        """Get a source by name."""
        return self._sources.get(name)

    def _parse_interval(self, value: str) -> timedelta:
        """Parse interval string to timedelta."""
        value = value.strip().lower()
        try:
            if value.endswith("h"):
                return timedelta(hours=int(value[:-1]))
            elif value.endswith("d"):
                return timedelta(days=int(value[:-1]))
            elif value.endswith("m"):
                return timedelta(minutes=int(value[:-1]))
        except ValueError:
            pass
        return timedelta(hours=24)  # Default: 24h

    def is_due_for_check(self, source: ResearchSource) -> bool:
        """Check if a source is due for a refresh based on check_interval."""
        if not source.enabled:
            return False
        if not source.last_checked:
            return True

        try:
            last = datetime.fromisoformat(source.last_checked)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            interval = self._parse_interval(source.check_interval)
            return datetime.now(timezone.utc) >= last + interval
        except (ValueError, TypeError):
            return True

    def get_due_sources(self) -> list[ResearchSource]:
        """Get all sources that are due for a check."""
        return [s for s in self._sources.values() if self.is_due_for_check(s)]

    def mark_checked(self, source_name: str) -> None:
        """Mark a source as checked right now."""
        if source_name in self._sources:
            self._sources[source_name].last_checked = datetime.now(timezone.utc).isoformat()
            self._save()

    def generate_briefing(self, findings: list[ResearchFinding]) -> str:
        """Generate a markdown briefing from research findings."""
        if not findings:
            return "📭 No new findings from monitored sources."

        lines = [
            "# 📡 Proactive Research Briefing",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Findings:** {len(findings)}",
            "",
        ]

        # Sort by relevance
        sorted_findings = sorted(findings, key=lambda f: f.relevance, reverse=True)

        for i, f in enumerate(sorted_findings, 1):
            relevance_bar = "🔴" if f.relevance >= 0.8 else "🟡" if f.relevance >= 0.5 else "⚪"
            lines.append(f"### {i}. {relevance_bar} {f.title}")
            lines.append(f"_{f.source_name}_ — {f.timestamp[:10]}")
            lines.append(f"{f.summary}")
            if f.url:
                lines.append(f"🔗 [Link]({f.url})")
            lines.append("")

        return "\n".join(lines)

    async def save_briefing(self, briefing: str, agent_name: str = "optimus") -> Path:
        """Save a briefing to the findings directory."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = FINDINGS_DIR / f"{agent_name}-{date}.md"
        path.write_text(briefing, encoding="utf-8")
        logger.info(f"Research: briefing saved to {path}")
        return path


# Singleton
proactive_researcher = ProactiveResearcher()
