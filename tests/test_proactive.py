"""
Tests for Phase 10 — Proactive Intelligence.
Session Bootstrap, Auto Journal, Reflection Engine, Cron Scheduler, Skills Discovery.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.engine.reflection_engine import ReflectionEngine, ReflectionReport
from src.memory.auto_journal import AutoJournal, CATEGORY_KEYWORDS
from src.memory.session_bootstrap import BootstrapContext, SessionBootstrap


# ============================================
# Session Bootstrap Tests
# ============================================
class TestBootstrapContext:
    def test_empty_context(self):
        ctx = BootstrapContext(agent_name="test")
        assert ctx.agent_name == "test"
        assert ctx.soul == ""
        assert not ctx.is_loaded

    def test_loaded_context(self):
        ctx = BootstrapContext(agent_name="test", soul="I am a tester.")
        assert ctx.is_loaded

    def test_build_prompt_empty(self):
        ctx = BootstrapContext(agent_name="test")
        assert ctx.build_prompt() == ""

    def test_build_prompt_with_data(self):
        ctx = BootstrapContext(
            agent_name="friday",
            soul="# SOUL.md — Friday\nDeveloper agent.",
            memory="### [2026-01-01] técnico\nFastAPI is fast.",
            daily_today="### [10:00:00] task_started\nWorking on deploy.",
        )
        prompt = ctx.build_prompt()
        assert "Session Context" in prompt
        assert "Identity" in prompt
        assert "Long-Term Memory" in prompt
        assert "Today's Activity" in prompt

    def test_build_prompt_truncates_long_memory(self):
        ctx = BootstrapContext(
            agent_name="test",
            soul="soul",
            memory="x" * 5000,
        )
        prompt = ctx.build_prompt()
        # Memory section should be truncated
        assert len(prompt) < 5000


class TestSessionBootstrap:
    def setup_method(self):
        self.bootstrap = SessionBootstrap()

    def test_instance_created(self):
        assert self.bootstrap is not None
        assert isinstance(self.bootstrap._cache, dict)

    def test_empty_cache(self):
        assert len(self.bootstrap._cache) == 0

    def test_invalidate(self):
        ctx = BootstrapContext(agent_name="test", soul="some soul")
        self.bootstrap._cache["test"] = ctx
        self.bootstrap.invalidate("test")
        assert "test" not in self.bootstrap._cache

    def test_invalidate_all(self):
        self.bootstrap._cache["a"] = BootstrapContext(agent_name="a")
        self.bootstrap._cache["b"] = BootstrapContext(agent_name="b")
        self.bootstrap.invalidate_all()
        assert len(self.bootstrap._cache) == 0
        assert len(self.bootstrap._file_hashes) == 0

    def test_hash_file_nonexistent(self):
        h = self.bootstrap._hash_file(Path("/nonexistent/file.md"))
        assert h == ""

    def test_hash_file_with_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Hello World")
            f.flush()
            h1 = self.bootstrap._hash_file(Path(f.name))
            assert len(h1) == 32  # MD5 hex

    def test_is_stale_when_no_cache(self):
        assert self.bootstrap._is_stale("uncached_agent")


# ============================================
# Auto Journal Tests
# ============================================
class TestAutoJournal:
    def setup_method(self):
        self.journal = AutoJournal()

    def test_instance_created(self):
        assert self.journal is not None

    def test_classify_relevance_high(self):
        result = self.journal._classify_relevance(
            "This is an important decision about the deploy configuration",
            "Always remember to check the error logs before deploying",
        )
        assert result == "high"

    def test_classify_relevance_low(self):
        result = self.journal._classify_relevance(
            "Bom dia!",
            "Bom dia! Como posso ajudar?",
        )
        assert result == "low"

    def test_detect_category_erros(self):
        category = self.journal._detect_category(
            "Tem um bug no código",
            "O traceback mostra uma exception no handler",
        )
        assert category == "erros"

    def test_detect_category_tecnico(self):
        category = self.journal._detect_category(
            "Preciso configurar o deploy",
            "Vou implementar o Dockerfile com a migration",
        )
        assert category == "técnico"

    def test_detect_category_general(self):
        category = self.journal._detect_category(
            "Olá",
            "Oi, tudo bem?",
        )
        assert category == "geral"

    def test_extract_learning(self):
        learning = self.journal._extract_learning(
            "Como configurar Docker?",
            "Primeiro, crie um Dockerfile com FROM python:3.12-slim. Depois configure o compose.",
            "técnico",
        )
        assert "[técnico]" in learning
        assert "Docker" in learning

    def test_deduplication(self):
        hash1 = self.journal._compute_hash("This is a learning about Python")
        hash2 = self.journal._compute_hash("This is a learning about Python")
        hash3 = self.journal._compute_hash("Different learning")
        assert hash1 == hash2
        assert hash1 != hash3

    def test_category_keywords_defined(self):
        assert "decisões" in CATEGORY_KEYWORDS
        assert "preferências" in CATEGORY_KEYWORDS
        assert "erros" in CATEGORY_KEYWORDS
        assert "conhecimento" in CATEGORY_KEYWORDS
        assert "técnico" in CATEGORY_KEYWORDS


# ============================================
# Reflection Engine Tests
# ============================================
class TestReflectionEngine:
    def setup_method(self):
        self.engine = ReflectionEngine()

    def test_instance_created(self):
        assert self.engine is not None

    def test_empty_report(self):
        report = ReflectionReport(
            agent_name="test",
            period_start="2026-01-01",
            period_end="2026-01-07",
        )
        assert report.total_interactions == 0
        assert report.topics == []
        assert report.gaps == []

    def test_report_to_markdown(self):
        report = ReflectionReport(
            agent_name="friday",
            period_start="2026-01-01",
            period_end="2026-01-07",
            total_interactions=42,
        )
        md = report.to_markdown()
        assert "friday" in md
        assert "42" in md

    def test_analyze_topics(self):
        text = "python python python docker docker sql api"
        topics = self.engine._analyze_topics(text)
        assert len(topics) > 0
        assert topics[0].topic == "python"  # Most frequent
        assert topics[0].count >= 3

    def test_detect_gaps_with_failures(self):
        text = (
            "### [10:00] task\nTentei resolver o bug de python mas não consigo\n"
            "### [11:00] task\nErro de python, não sei como corrigir\n"
            "### [12:00] task\nNovo erro de python critical\n"
        )
        gaps = self.engine._detect_gaps(text)
        # Should detect python as a gap topic
        python_gaps = [g for g in gaps if g.topic == "python"]
        assert len(python_gaps) > 0

    def test_detect_gaps_no_failures(self):
        text = "### [10:00] task\nTudo funcionou perfeitamente com docker e python"
        gaps = self.engine._detect_gaps(text)
        assert len(gaps) == 0

    def test_generate_suggestions_no_interactions(self):
        report = ReflectionReport(
            agent_name="test",
            period_start="2026-01-01",
            period_end="2026-01-07",
            total_interactions=0,
        )
        suggestions = self.engine._generate_suggestions(report)
        assert len(suggestions) > 0
        assert "frequência" in suggestions[0].lower() or "uso" in suggestions[0].lower()


# ============================================
# Cron Scheduler Tests
# ============================================
class TestCronScheduler:
    """Tests for CronScheduler — uses isolated temp dir for persistence."""

    def setup_method(self):
        # Import here to get a fresh instance with temp dir
        from src.core.cron_scheduler import CronJob, CronScheduler

        self.CronJob = CronJob
        self.scheduler = CronScheduler()
        # Clear any loaded jobs for clean test
        self.scheduler._jobs.clear()

    def test_add_job(self):
        job = self.CronJob(
            name="Test Job",
            schedule_type="at",
            schedule_value="2026-12-31T23:59:59Z",
            payload="Hello from cron!",
        )
        job_id = self.scheduler.add(job)
        assert job_id == job.id
        assert job.id in self.scheduler._jobs

    def test_remove_job(self):
        job = self.CronJob(name="To Remove", schedule_type="at", schedule_value="2026-12-31T00:00:00Z")
        self.scheduler.add(job)
        assert self.scheduler.remove(job.id)
        assert job.id not in self.scheduler._jobs

    def test_remove_nonexistent(self):
        assert not self.scheduler.remove("nonexistent-id")

    def test_list_jobs(self):
        j1 = self.CronJob(name="Job 1", schedule_type="at", schedule_value="2026-06-01T00:00:00Z")
        j2 = self.CronJob(name="Job 2", schedule_type="at", schedule_value="2026-07-01T00:00:00Z", enabled=False)
        self.scheduler.add(j1)
        self.scheduler.add(j2)

        all_jobs = self.scheduler.list_jobs()
        assert len(all_jobs) == 2

        enabled_jobs = self.scheduler.list_jobs(enabled_only=True)
        assert len(enabled_jobs) == 1
        assert enabled_jobs[0].name == "Job 1"

    def test_get_job(self):
        job = self.CronJob(name="Findable", schedule_type="at", schedule_value="2026-01-01T00:00:00Z")
        self.scheduler.add(job)
        found = self.scheduler.get(job.id)
        assert found is not None
        assert found.name == "Findable"

    def test_parse_interval(self):
        assert self.scheduler._parse_interval("30m") == timedelta(minutes=30)
        assert self.scheduler._parse_interval("1h") == timedelta(hours=1)
        assert self.scheduler._parse_interval("7d") == timedelta(days=7)
        assert self.scheduler._parse_interval("60s") == timedelta(seconds=60)
        assert self.scheduler._parse_interval("invalid") is None

    def test_is_due_future_job(self):
        job = self.CronJob(
            name="Future",
            schedule_type="at",
            schedule_value=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        job.next_run = job.schedule_value
        assert not self.scheduler._is_due(job)

    def test_is_due_past_job(self):
        job = self.CronJob(
            name="Past",
            schedule_type="at",
            schedule_value=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )
        job.next_run = job.schedule_value
        assert self.scheduler._is_due(job)

    def test_is_due_disabled(self):
        job = self.CronJob(
            name="Disabled",
            schedule_type="at",
            schedule_value=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            enabled=False,
        )
        job.next_run = job.schedule_value
        assert not self.scheduler._is_due(job)

    def test_job_serialization(self):
        job = self.CronJob(name="Serialize Me", schedule_type="every", schedule_value="1h")
        d = job.to_dict()
        assert d["name"] == "Serialize Me"
        restored = self.CronJob.from_dict(d)
        assert restored.name == "Serialize Me"
        assert restored.schedule_type == "every"


# ============================================
# Skills Discovery Tests
# ============================================
class TestSkillsDiscovery:
    def setup_method(self):
        from src.skills.skills_discovery import SkillsDiscovery

        self.discovery = SkillsDiscovery()

    def test_instance_created(self):
        assert self.discovery is not None

    def test_tokenize(self):
        tokens = self.discovery._tokenize("Hello World Python Docker")
        assert "hello" in tokens
        assert "python" in tokens
        assert "docker" in tokens

    def test_tokenize_removes_stopwords(self):
        tokens = self.discovery._tokenize("a the in for and with")
        assert len(tokens) == 0

    def test_search_empty_query(self):
        results = self.discovery.search("")
        assert results == []

    def test_suggest_empty_query(self):
        suggestions = self.discovery.suggest_for_query("")
        assert suggestions == []

    def test_get_stats(self):
        stats = self.discovery.get_stats()
        assert "indexed_skills" in stats
        assert "total_terms" in stats
        assert "categories" in stats
        assert isinstance(stats["indexed_skills"], int)
