"""
Tests for Phase 6 — Polish: Security, Performance, Events, Skills, Agents.
"""

import pytest
from datetime import datetime, timedelta, timezone

from src.core.security import (
    Permission, SandboxLevel, SecurityManager, PERMISSION_MATRIX, SANDBOX_BY_LEVEL,
)
from src.core.performance import (
    ContextCompactor, QueryCache, SessionPruner,
)
from src.core.events import Event, EventBus, EventType, HeartbeatManager, WebhookReceiver
from src.skills.skills_registry import Skill, SkillsRegistry


# ============================================
# Security Tests
# ============================================
class TestSecurity:
    def setup_method(self):
        self.sec = SecurityManager()

    def test_lead_has_all_permissions(self):
        assert len(PERMISSION_MATRIX["lead"]) == 8

    def test_intern_limited_permissions(self):
        perms = PERMISSION_MATRIX["intern"]
        assert Permission.DB_WRITE not in perms
        assert Permission.FS_WRITE not in perms
        assert Permission.SYSTEM_CONFIG not in perms
        assert Permission.DB_READ in perms

    def test_check_permission_allowed(self):
        result = self.sec.check_permission("optimus", "lead", Permission.DB_WRITE)
        assert result is True

    def test_check_permission_denied(self):
        result = self.sec.check_permission("intern_bot", "intern", Permission.DB_WRITE)
        assert result is False

    def test_sandbox_levels(self):
        assert SANDBOX_BY_LEVEL["lead"] == SandboxLevel.FULL_ACCESS
        assert SANDBOX_BY_LEVEL["intern"] == SandboxLevel.ISOLATED

    def test_grant_custom_permission(self):
        self.sec.grant_permission("special_intern", Permission.FS_WRITE)
        perms = self.sec.get_permissions("special_intern", "intern")
        assert Permission.FS_WRITE in perms

    def test_revoke_custom_permission(self):
        self.sec.grant_permission("agent", Permission.NETWORK)
        self.sec.revoke_permission("agent", Permission.NETWORK)
        perms = self.sec.get_permissions("agent", "intern")
        assert Permission.NETWORK not in perms

    def test_audit_trail(self):
        self.sec.check_permission("bot", "intern", Permission.DB_WRITE)
        audit = self.sec.get_audit_log(agent_name="bot")
        assert len(audit) >= 1
        assert audit[0].allowed is False

    def test_audit_action(self):
        self.sec.audit_action("optimus", "file_created", resource="/test.py")
        audit = self.sec.get_audit_log(action="file_created")
        assert len(audit) == 1

    def test_denied_actions(self):
        self.sec.check_permission("bot", "intern", Permission.SYSTEM_CONFIG)
        denied = self.sec.get_denied_actions()
        assert len(denied) >= 1

    def test_audit_stats(self):
        self.sec.check_permission("a", "lead", Permission.DB_READ)
        self.sec.check_permission("b", "intern", Permission.DB_WRITE)
        stats = self.sec.get_audit_stats()
        assert stats["total_entries"] >= 2


# ============================================
# Performance Tests
# ============================================
class TestSessionPruner:
    def setup_method(self):
        self.pruner = SessionPruner(ttl_hours=1, max_sessions=5)

    def test_register_session(self):
        info = self.pruner.register_session("s1", "optimus")
        assert info.session_id == "s1"

    @pytest.mark.asyncio
    async def test_prune_expired(self):
        info = self.pruner.register_session("old")
        info.last_active = datetime.now(timezone.utc) - timedelta(hours=2)
        pruned = await self.pruner.prune()
        assert pruned == 1

    @pytest.mark.asyncio
    async def test_prune_max_sessions(self):
        for i in range(8):
            self.pruner.register_session(f"s{i}")
        pruned = await self.pruner.prune()
        assert self.pruner.get_active_count() <= 5

    def test_touch_session(self):
        self.pruner.register_session("s1")
        self.pruner.touch_session("s1", tokens=100)
        stats = self.pruner.get_stats()
        assert stats["total_tokens"] == 100


class TestContextCompactor:
    def setup_method(self):
        self.compactor = ContextCompactor(max_messages=10)

    @pytest.mark.asyncio
    async def test_no_compact_small_history(self):
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
        result = await self.compactor.compact(messages)
        assert not result["compacted"]

    @pytest.mark.asyncio
    async def test_compact_large_history(self):
        messages = [{"role": "user", "content": f"message {i}"} for i in range(30)]
        result = await self.compactor.compact(messages)
        assert result["compacted"]
        assert result["compacted_count"] < 30

    def test_estimate_tokens(self):
        messages = [{"role": "user", "content": "a" * 400}]
        tokens = self.compactor.estimate_tokens(messages)
        assert tokens == 100


class TestQueryCache:
    def setup_method(self):
        self.cache = QueryCache(max_size=3, ttl_seconds=60)

    def test_set_and_get(self):
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

    def test_miss(self):
        assert self.cache.get("nonexistent") is None

    def test_eviction(self):
        self.cache.set("a", "1")
        self.cache.set("b", "2")
        self.cache.set("c", "3")
        self.cache.set("d", "4")  # Should evict oldest
        assert self.cache.get("a") is None

    def test_stats(self):
        self.cache.set("k", "v")
        self.cache.get("k")  # hit
        self.cache.get("miss")  # miss
        stats = self.cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "50.0%"

    def test_invalidate(self):
        self.cache.set("k", "v")
        self.cache.invalidate("k")
        assert self.cache.get("k") is None

    def test_clear(self):
        self.cache.set("a", "1")
        self.cache.set("b", "2")
        self.cache.clear()
        assert self.cache.get_stats()["size"] == 0


# ============================================
# Event System Tests
# ============================================
class TestEventBus:
    def setup_method(self):
        self.bus = EventBus()

    @pytest.mark.asyncio
    async def test_emit_and_handle(self):
        received = []

        async def handler(event: Event):
            received.append(event)

        self.bus.on("test.event", handler)
        await self.bus.emit(Event(type="test.event", source="test"))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_wildcard_handler(self):
        received = []

        async def handler(event: Event):
            received.append(event)

        self.bus.on("*", handler)
        await self.bus.emit(Event(type="any.event", source="test"))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        received = []

        async def handler(event: Event):
            received.append(event)

        self.bus.on("test", handler)
        self.bus.off("test", handler)
        await self.bus.emit(Event(type="test", source="test"))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_recent_events(self):
        await self.bus.emit_simple("a.b", source="s1")
        await self.bus.emit_simple("c.d", source="s2")
        events = self.bus.get_recent_events(limit=10)
        assert len(events) == 2


class TestHeartbeatManager:
    def setup_method(self):
        self.bus = EventBus()
        self.hb = HeartbeatManager(self.bus, interval_minutes=1)

    def test_register_agent(self):
        self.hb.register_agent("optimus")
        assert self.hb.is_alive("optimus")

    def test_unknown_agent_not_alive(self):
        assert not self.hb.is_alive("ghost")

    @pytest.mark.asyncio
    async def test_beat(self):
        self.hb.register_agent("friday")
        await self.hb.beat("friday")
        assert self.hb.is_alive("friday")

    def test_get_status(self):
        self.hb.register_agent("optimus")
        status = self.hb.get_status()
        assert "optimus" in status
        assert status["optimus"]["alive"] is True


class TestWebhookReceiver:
    def setup_method(self):
        self.bus = EventBus()
        self.wh = WebhookReceiver(self.bus)

    @pytest.mark.asyncio
    async def test_process_webhook(self):
        result = await self.wh.process_webhook("generic", {"data": "test"})
        assert result["status"] == "received"

    @pytest.mark.asyncio
    async def test_process_with_custom_processor(self):
        async def github_proc(payload, headers):
            return {"processed": True}

        self.wh.register_processor("github", github_proc)
        result = await self.wh.process_webhook("github", {"action": "push"})
        assert result["status"] == "processed"


# ============================================
# Skills Registry Tests
# ============================================
class TestSkillsRegistry:
    def setup_method(self):
        self.registry = SkillsRegistry()

    def test_builtin_skills_loaded(self):
        skills = self.registry.list_skills()
        assert len(skills) >= 8

    def test_install_skill(self):
        skill = Skill(name="custom_skill", description="A custom skill", category="custom")
        self.registry.install(skill)
        assert self.registry.get("custom_skill") is not None

    def test_uninstall_skill(self):
        skill = Skill(name="removable", description="Will be removed")
        self.registry.install(skill)
        assert self.registry.uninstall("removable") is True
        assert self.registry.get("removable") is None

    def test_filter_by_category(self):
        code_skills = self.registry.list_skills(category="code")
        assert all(s.category == "code" for s in code_skills)

    def test_disable_enable(self):
        self.registry.disable("code_generation")
        disabled = self.registry.get("code_generation")
        assert disabled.enabled is False

        self.registry.enable("code_generation")
        enabled = self.registry.get("code_generation")
        assert enabled.enabled is True

    def test_get_categories(self):
        categories = self.registry.get_categories()
        assert "code" in categories
        assert "research" in categories

    def test_generate_catalogue(self):
        catalogue = self.registry.generate_catalogue()
        assert "Skills Catalogue" in catalogue
        assert "code_generation" in catalogue

    @pytest.mark.asyncio
    async def test_load_nonexistent_dir(self):
        count = await self.registry.load_from_directory("/nonexistent/skills")
        assert count == 0
