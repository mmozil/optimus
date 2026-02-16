"""
Agent Optimus — Proactive Researcher (Fase 11: Jarvis Mode).
When idle, proactively monitors configurable sources (RSS, GitHub, URLs)
for topics of interest and generates briefings. Rate-limited by source.

Phase 11 completion: real fetchers for RSS, GitHub API, and URL scraping.
"""

import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

RESEARCH_DIR = Path(__file__).parent.parent.parent / "workspace" / "research"
SOURCES_FILE = RESEARCH_DIR / "sources.json"
FINDINGS_DIR = RESEARCH_DIR / "findings"

# GitHub API (public, no token required for basic access)
GITHUB_API_BASE = "https://api.github.com"
DEFAULT_HTTP_TIMEOUT = 15.0


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
    - Real fetchers: RSS (XML), GitHub API (releases/commits), URL (HTML meta)
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

    # ============================================
    # Real Fetchers
    # ============================================

    async def fetch_rss(self, source: ResearchSource) -> list[ResearchFinding]:
        """
        Fetch and parse an RSS/Atom feed.

        Uses xml.etree.ElementTree for parsing (no extra dependency).
        """
        findings: list[ResearchFinding] = []

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT, follow_redirects=True) as client:
                response = await client.get(source.url)
                response.raise_for_status()

            root = ET.fromstring(response.text)

            # Handle RSS 2.0
            items = root.findall(".//item")
            # Handle Atom
            if not items:
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                items = root.findall(".//atom:entry", ns)

            for item in items[:10]:  # Limit to 10 most recent
                title = self._xml_text(item, "title") or self._xml_text(
                    item, "{http://www.w3.org/2005/Atom}title"
                )
                description = (
                    self._xml_text(item, "description")
                    or self._xml_text(item, "{http://www.w3.org/2005/Atom}summary")
                    or ""
                )
                link = self._xml_text(item, "link") or ""
                if not link:
                    link_elem = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_elem is not None:
                        link = link_elem.get("href", "")

                if title:
                    # Strip HTML tags from description
                    clean_desc = re.sub(r"<[^>]+>", "", description)[:300]
                    findings.append(ResearchFinding(
                        title=title,
                        summary=clean_desc,
                        source_name=source.name,
                        url=link,
                        relevance=self._score_relevance(title, clean_desc, source.tags),
                    ))

            logger.info(f"Research RSS: {source.name} → {len(findings)} items")

        except httpx.HTTPError as e:
            logger.error(f"Research RSS error ({source.name}): {e}")
        except ET.ParseError as e:
            logger.error(f"Research RSS parse error ({source.name}): {e}")

        return findings

    async def fetch_github(self, source: ResearchSource) -> list[ResearchFinding]:
        """
        Fetch recent releases and commits from a GitHub repository.

        URL format: https://github.com/{owner}/{repo}
        Uses GitHub public API (60 req/h without token, 5000 with).
        """
        findings: list[ResearchFinding] = []

        # Extract owner/repo from URL
        match = re.search(r"github\.com/([^/]+)/([^/]+)", source.url)
        if not match:
            logger.warning(f"Research GitHub: invalid URL format: {source.url}")
            return findings

        owner, repo = match.group(1), match.group(2).rstrip(".git")

        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            async with httpx.AsyncClient(
                timeout=DEFAULT_HTTP_TIMEOUT,
                headers=headers,
                follow_redirects=True,
            ) as client:
                # Fetch latest releases
                releases_resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases",
                    params={"per_page": 5},
                )
                if releases_resp.status_code == 200:
                    for release in releases_resp.json()[:5]:
                        findings.append(ResearchFinding(
                            title=f"📦 {repo}: {release.get('name') or release.get('tag_name', 'Release')}",
                            summary=(release.get("body") or "No description")[:300],
                            source_name=source.name,
                            url=release.get("html_url", ""),
                            relevance=0.8,
                        ))

                # Fetch recent commits (last 5)
                commits_resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
                    params={"per_page": 5},
                )
                if commits_resp.status_code == 200:
                    for commit in commits_resp.json()[:5]:
                        msg = commit.get("commit", {}).get("message", "")
                        first_line = msg.split("\n")[0][:200]
                        findings.append(ResearchFinding(
                            title=f"🔨 {repo}: {first_line}",
                            summary=f"by {commit.get('commit', {}).get('author', {}).get('name', 'unknown')}",
                            source_name=source.name,
                            url=commit.get("html_url", ""),
                            relevance=0.5,
                        ))

            logger.info(f"Research GitHub: {source.name} → {len(findings)} items")

        except httpx.HTTPError as e:
            logger.error(f"Research GitHub error ({source.name}): {e}")

        return findings

    async def fetch_url(self, source: ResearchSource) -> list[ResearchFinding]:
        """
        Fetch a URL and extract title and meta description from HTML.

        Useful for monitoring landing pages, status pages, etc.
        """
        findings: list[ResearchFinding] = []

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT, follow_redirects=True) as client:
                response = await client.get(source.url)
                response.raise_for_status()

            html = response.text

            # Extract <title>
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else source.name

            # Extract <meta name="description">
            desc_match = re.search(
                r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                html,
                re.IGNORECASE,
            )
            description = desc_match.group(1).strip() if desc_match else ""

            findings.append(ResearchFinding(
                title=title[:200],
                summary=description[:300] or f"Page fetched from {source.url}",
                source_name=source.name,
                url=source.url,
                relevance=self._score_relevance(title, description, source.tags),
            ))

            logger.info(f"Research URL: {source.name} → '{title[:50]}'")

        except httpx.HTTPError as e:
            logger.error(f"Research URL error ({source.name}): {e}")

        return findings

    async def check_source(self, source: ResearchSource) -> list[ResearchFinding]:
        """
        Check a single source using the appropriate fetcher.

        Dispatches to fetch_rss, fetch_github, or fetch_url based on source.type.
        """
        fetchers = {
            "rss": self.fetch_rss,
            "github": self.fetch_github,
            "url": self.fetch_url,
        }

        fetcher = fetchers.get(source.type)
        if not fetcher:
            logger.warning(f"Research: unknown source type '{source.type}' for '{source.name}'")
            return []

        findings = await fetcher(source)
        self.mark_checked(source.name)
        return findings

    async def run_check_cycle(self) -> list[ResearchFinding]:
        """
        Run a full check cycle: find all due sources, fetch them, return findings.

        This is the main entry point for scheduled research checks.
        """
        due = self.get_due_sources()
        if not due:
            logger.debug("Research: no sources due for check")
            return []

        all_findings: list[ResearchFinding] = []
        for source in due:
            findings = await self.check_source(source)
            all_findings.extend(findings)

        logger.info(f"Research cycle: checked {len(due)} sources, found {len(all_findings)} items")
        return all_findings

    # ============================================
    # Briefing Generation
    # ============================================

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

    # ============================================
    # Helpers
    # ============================================

    @staticmethod
    def _xml_text(element: ET.Element, tag: str) -> str:
        """Safely extract text from an XML element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return ""

    @staticmethod
    def _score_relevance(title: str, description: str, tags: list[str]) -> float:
        """Score relevance of a finding based on tag matches."""
        if not tags:
            return 0.5  # Default: medium relevance

        text = f"{title} {description}".lower()
        matches = sum(1 for tag in tags if tag.lower() in text)
        if matches == 0:
            return 0.3
        return min(0.5 + (matches * 0.2), 1.0)


# Singleton
proactive_researcher = ProactiveResearcher()
