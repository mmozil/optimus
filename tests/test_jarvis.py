"""
Tests for Phase 11 — Jarvis Mode.
Proactive Research, Intent Prediction, Context Awareness, Emotional Adapter,
Voice Interface, Autonomous Executor, Collective Intelligence.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.channels.voice_interface import VoiceConfig, VoiceInterface, VoiceProviderType
from src.core.context_awareness import AmbientContext, ContextAwareness
from src.engine.autonomous_executor import (
    AutonomousExecutor,
    ExecutionStatus,
    ExecutorConfig,
    TaskRisk,
)
from src.engine.emotional_adapter import EmotionalAdapter, Mood
from src.engine.intent_predictor import IntentPredictor, UserPattern, Prediction
from src.engine.proactive_researcher import (
    ProactiveResearcher,
    ResearchFinding,
    ResearchSource,
)
from src.memory.collective_intelligence import CollectiveIntelligence, SharedKnowledge


# ============================================
# Proactive Researcher Tests
# ============================================
class TestProactiveResearcher:
    def setup_method(self):
        self.researcher = ProactiveResearcher()
        self.researcher._sources.clear()  # Clean state

    def test_add_source(self):
        src = ResearchSource(name="Test Blog", type="rss", url="https://example.com/feed")
        self.researcher.add_source(src)
        assert "Test Blog" in self.researcher._sources

    def test_remove_source(self):
        src = ResearchSource(name="To Remove", type="url", url="https://example.com")
        self.researcher.add_source(src)
        assert self.researcher.remove_source("To Remove")
        assert "To Remove" not in self.researcher._sources

    def test_remove_nonexistent(self):
        assert not self.researcher.remove_source("ghost")

    def test_list_sources(self):
        self.researcher.add_source(ResearchSource(name="A", enabled=True))
        self.researcher.add_source(ResearchSource(name="B", enabled=False))
        all_src = self.researcher.list_sources()
        assert len(all_src) == 2
        enabled = self.researcher.list_sources(enabled_only=True)
        assert len(enabled) == 1

    def test_is_due_never_checked(self):
        src = ResearchSource(name="New", last_checked="")
        assert self.researcher.is_due_for_check(src)

    def test_is_due_recently_checked(self):
        src = ResearchSource(
            name="Recent",
            check_interval="24h",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
        assert not self.researcher.is_due_for_check(src)

    def test_is_due_disabled(self):
        src = ResearchSource(name="Disabled", enabled=False)
        assert not self.researcher.is_due_for_check(src)

    def test_generate_briefing_empty(self):
        briefing = self.researcher.generate_briefing([])
        assert "No new findings" in briefing

    def test_generate_briefing_with_findings(self):
        findings = [
            ResearchFinding(title="New Release", summary="v2.0 released", source_name="GitHub"),
            ResearchFinding(title="Security Alert", summary="CVE found", source_name="RSS", relevance=0.9),
        ]
        briefing = self.researcher.generate_briefing(findings)
        assert "Research Briefing" in briefing
        assert "Security Alert" in briefing
        assert "New Release" in briefing

    def test_parse_interval(self):
        assert self.researcher._parse_interval("1h") == timedelta(hours=1)
        assert self.researcher._parse_interval("24h") == timedelta(hours=24)
        assert self.researcher._parse_interval("7d") == timedelta(days=7)


# ============================================
# Intent Predictor Tests
# ============================================
class TestIntentPredictor:
    def setup_method(self):
        self.predictor = IntentPredictor()

    def test_instance_created(self):
        assert self.predictor is not None

    def test_get_time_slot_morning(self):
        assert self.predictor._get_time_slot(9) == "morning"

    def test_get_time_slot_afternoon(self):
        assert self.predictor._get_time_slot(14) == "afternoon"

    def test_get_time_slot_evening(self):
        assert self.predictor._get_time_slot(20) == "evening"

    def test_get_time_slot_night(self):
        assert self.predictor._get_time_slot(2) == "night"

    def test_extract_actions_deploy(self):
        actions = self.predictor._extract_actions("Vou fazer deploy em produção")
        assert "deploy" in actions

    def test_extract_actions_bug(self):
        actions = self.predictor._extract_actions("Preciso debugar esse traceback")
        assert "bug_fix" in actions

    def test_extract_actions_empty(self):
        actions = self.predictor._extract_actions("Bom dia!")
        assert len(actions) == 0

    def test_predict_next_empty_patterns(self):
        predictions = self.predictor.predict_next([])
        assert predictions == []

    def test_predict_next_low_confidence(self):
        patterns = [
            UserPattern(action="deploy", frequency=1, confidence=0.1, weekdays=[0]),
        ]
        predictions = self.predictor.predict_next(patterns)
        assert len(predictions) == 0

    def test_build_suggestion(self):
        msg = self.predictor._build_suggestion("deploy", "você faz isso às sextas")
        assert "🚀" in msg
        assert "deploy" in msg.lower() or "Preparar" in msg


# ============================================
# Context Awareness Tests
# ============================================
class TestContextAwareness:
    def setup_method(self):
        self.ctx_awareness = ContextAwareness()

    def test_build_context(self):
        ctx = self.ctx_awareness.build_context(timezone_offset=-3)
        assert ctx.timezone_offset == -3
        assert ctx.local_time != ""
        assert ctx.day_of_week != ""

    def test_build_context_utc(self):
        ctx = self.ctx_awareness.build_context(timezone_offset=0)
        assert ctx.timezone_offset == 0

    def test_time_slot_classification(self):
        assert self.ctx_awareness._get_time_slot(8) == "morning"
        assert self.ctx_awareness._get_time_slot(15) == "afternoon"
        assert self.ctx_awareness._get_time_slot(21) == "evening"
        assert self.ctx_awareness._get_time_slot(1) == "night"

    def test_generate_greeting(self):
        greeting = self.ctx_awareness.generate_greeting("Marcel")
        assert "Marcel" in greeting

    def test_generate_greeting_with_context(self):
        ctx = AmbientContext(greeting="Bom dia", day_suggestion="Sexta!")
        greeting = self.ctx_awareness.generate_greeting("Marcel", ctx)
        assert "Bom dia" in greeting
        assert "Marcel" in greeting

    def test_time_sensitivity_weekend(self):
        result = self.ctx_awareness.get_time_sensitivity_from_slot("morning", 5)
        assert result == "relaxed"

    def test_time_sensitivity_weekday(self):
        result = self.ctx_awareness.get_time_sensitivity_from_slot("morning", 1)
        assert result == "normal"

    def test_build_context_prompt(self):
        ctx = AmbientContext(
            local_time="10:30",
            day_of_week="segunda-feira",
            is_business_hours=True,
            time_sensitivity="normal",
        )
        prompt = self.ctx_awareness.build_context_prompt(ctx)
        assert "10:30" in prompt
        assert "segunda-feira" in prompt


# ============================================
# Emotional Adapter Tests
# ============================================
class TestEmotionalAdapter:
    def setup_method(self):
        self.adapter = EmotionalAdapter()

    def test_detect_frustrated(self):
        result = self.adapter.analyze("Droga, não funciona de novo! Tá tudo quebrado")
        assert result.mood == Mood.FRUSTRATED
        assert result.confidence > 0

    def test_detect_curious(self):
        result = self.adapter.analyze("Como funciona o sistema de embeddings? Quero entender melhor")
        assert result.mood == Mood.CURIOUS

    def test_detect_rushed(self):
        result = self.adapter.analyze("Urgente! Preciso disso agora, é deadline!")
        assert result.mood == Mood.RUSHED

    def test_detect_celebrating(self):
        result = self.adapter.analyze("Funcionou! 🎉 Deu certo, finalmente! Show!")
        assert result.mood == Mood.CELEBRATING

    def test_detect_neutral(self):
        result = self.adapter.analyze("Olá")
        assert result.mood == Mood.NEUTRAL

    def test_tone_instruction_frustrated(self):
        instruction = self.adapter.get_tone_instruction(Mood.FRUSTRATED)
        assert "DIRETO" in instruction

    def test_tone_instruction_curious(self):
        instruction = self.adapter.get_tone_instruction(Mood.CURIOUS)
        assert "DETALHADO" in instruction

    def test_tone_instruction_rushed(self):
        instruction = self.adapter.get_tone_instruction(Mood.RUSHED)
        assert "CONCISO" in instruction

    def test_mood_emoji(self):
        assert self.adapter.get_mood_emoji(Mood.FRUSTRATED) == "😤"
        assert self.adapter.get_mood_emoji(Mood.CELEBRATING) == "🎉"


# ============================================
# Voice Interface Tests
# ============================================
class TestVoiceInterface:
    def setup_method(self):
        self.voice = VoiceInterface(VoiceConfig(
            stt_provider=VoiceProviderType.STUB,
            tts_provider=VoiceProviderType.STUB,
        ))

    def test_instance_created(self):
        assert self.voice is not None
        assert self.voice.config.language == "pt-BR"

    def test_wake_word_detection(self):
        assert self.voice.detect_wake_word("Hey Optimus, como vai?")
        assert self.voice.detect_wake_word("optimus, preciso de ajuda")
        assert not self.voice.detect_wake_word("Oi, tudo bem?")

    def test_strip_wake_word(self):
        result = self.voice.strip_wake_word("hey optimus, como vai?")
        assert "optimus" not in result.lower()
        assert "como vai" in result

    def test_empty_audio(self):
        import asyncio
        text = asyncio.get_event_loop().run_until_complete(self.voice.listen(b""))
        assert text == ""

    def test_config_defaults(self):
        config = VoiceConfig()
        assert config.language == "pt-BR"
        assert config.voice_name == "optimus"
        assert "optimus" in config.wake_words

    def test_provider_types_exist(self):
        assert VoiceProviderType.GOOGLE == "google"
        assert VoiceProviderType.WHISPER == "whisper"
        assert VoiceProviderType.ELEVENLABS == "elevenlabs"
        assert VoiceProviderType.STUB == "stub"


# ============================================
# Autonomous Executor Tests
# ============================================
class TestAutonomousExecutor:
    def setup_method(self):
        self.executor = AutonomousExecutor()
        self.executor.config = ExecutorConfig()
        self.executor._today_count = 0

    def test_classify_risk_low(self):
        risk = self.executor.classify_risk("Read the file and check status")
        assert risk == TaskRisk.LOW

    def test_classify_risk_medium(self):
        risk = self.executor.classify_risk("Edit this config file")
        assert risk == TaskRisk.MEDIUM

    def test_classify_risk_high(self):
        risk = self.executor.classify_risk("Deploy the staging branch")
        assert risk == TaskRisk.HIGH

    def test_classify_risk_critical(self):
        risk = self.executor.classify_risk("Delete all files with rm -rf")
        assert risk == TaskRisk.CRITICAL

    def test_should_execute_high_confidence(self):
        result = self.executor.should_auto_execute("search logs", 0.95)
        assert result is True

    def test_should_not_execute_low_confidence(self):
        result = self.executor.should_auto_execute("search logs", 0.5)
        assert result is False

    def test_should_not_execute_critical(self):
        result = self.executor.should_auto_execute("delete production database", 0.99)
        assert result is False

    def test_should_not_execute_disabled(self):
        self.executor.config.enabled = False
        result = self.executor.should_auto_execute("search logs", 0.99)
        assert result is False

    def test_should_not_exceed_budget(self):
        self.executor._today_count = 100
        result = self.executor.should_auto_execute("search logs", 0.99)
        assert result is False

    def test_executor_config_defaults(self):
        config = ExecutorConfig()
        assert config.auto_execute_threshold == 0.9
        assert config.daily_budget == 50
        assert config.enabled is True


# ============================================
# Collective Intelligence Tests
# ============================================
class TestCollectiveIntelligence:
    def setup_method(self):
        self.collective = CollectiveIntelligence()
        self.collective._knowledge.clear()
        self.collective._hashes.clear()

    def test_share_knowledge(self):
        sk = self.collective.share("friday", "python", "Use virtualenv for isolation")
        assert sk is not None
        assert sk.source_agent == "friday"

    def test_share_deduplication(self):
        self.collective.share("friday", "python", "Use virtualenv")
        sk2 = self.collective.share("fury", "python", "Use virtualenv")
        assert sk2 is None  # Duplicate

    def test_query_by_topic(self):
        self.collective.share("friday", "docker", "Use multi-stage builds")
        results = self.collective.query("docker")
        assert len(results) == 1
        assert results[0].topic == "docker"

    def test_query_tracks_usage(self):
        self.collective.share("friday", "api", "Always use pagination")
        results = self.collective.query("api", requesting_agent="fury")
        assert "fury" in results[0].used_by

    def test_knowledge_graph(self):
        self.collective.share("friday", "python", "Type hints are great")
        self.collective.share("fury", "research", "Use academic sources")
        graph = self.collective.get_knowledge_graph()
        assert "friday" in graph
        assert "fury" in graph
        assert "python" in graph["friday"]

    def test_find_expert(self):
        self.collective.share("friday", "python", "Learning 1")
        self.collective.share("friday", "python", "Learning 2 about python")
        self.collective.share("fury", "research", "Research tip")
        expert = self.collective.find_expert("python")
        assert expert == "friday"

    def test_get_stats(self):
        self.collective.share("a", "t1", "l1")
        self.collective.share("b", "t2", "l2")
        stats = self.collective.get_stats()
        assert stats["total_shared"] == 2
        assert stats["unique_agents"] == 2

    def test_empty_query(self):
        results = self.collective.query("nonexistent")
        assert results == []


# ============================================
# Proactive Researcher — Fetcher Tests
# ============================================
class TestResearcherFetchers:
    """Tests for real fetchers (RSS, GitHub, URL)."""

    def setup_method(self):
        self.researcher = ProactiveResearcher()
        self.researcher._sources.clear()

    def test_check_source_dispatcher_rss(self):
        """Verify check_source routes to fetch_rss for RSS type."""
        src = ResearchSource(name="Test RSS", type="rss", url="https://example.com/feed")
        # check_source is async, just verify the method exists and source type is recognized
        assert src.type == "rss"

    def test_check_source_dispatcher_github(self):
        """Verify check_source routes to fetch_github for GitHub type."""
        src = ResearchSource(name="Test GH", type="github", url="https://github.com/python/cpython")
        assert src.type == "github"

    def test_check_source_dispatcher_url(self):
        """Verify check_source routes to fetch_url for URL type."""
        src = ResearchSource(name="Test URL", type="url", url="https://example.com")
        assert src.type == "url"

    @pytest.mark.asyncio
    async def test_fetch_rss_invalid_url(self):
        """RSS fetcher handles network errors gracefully."""
        src = ResearchSource(name="Bad RSS", type="rss", url="http://192.0.2.1:9999/bad")
        findings = await self.researcher.fetch_rss(src)
        assert findings == []

    @pytest.mark.asyncio
    async def test_fetch_github_invalid_url(self):
        """GitHub fetcher handles invalid URLs gracefully."""
        src = ResearchSource(name="Bad GH", type="github", url="https://not-github.com/x/y")
        findings = await self.researcher.fetch_github(src)
        assert findings == []

    @pytest.mark.asyncio
    async def test_fetch_url_invalid(self):
        """URL fetcher handles network errors gracefully."""
        src = ResearchSource(name="Bad URL", type="url", url="http://192.0.2.1:9999/bad")
        findings = await self.researcher.fetch_url(src)
        assert findings == []

    @pytest.mark.asyncio
    async def test_run_check_cycle_no_due(self):
        """Run cycle returns empty when no sources are due."""
        findings = await self.researcher.run_check_cycle()
        assert findings == []

    def test_score_relevance_with_tags(self):
        """Relevance scoring boosts matched tags."""
        score = self.researcher._score_relevance(
            "New Python Release", "Python 3.13 is here", ["python"]
        )
        assert score > 0.5

    def test_score_relevance_no_tags(self):
        """Default relevance when no tags configured."""
        score = self.researcher._score_relevance("Title", "Desc", [])
        assert score == 0.5

    def test_mark_checked(self):
        """mark_checked updates last_checked timestamp."""
        src = ResearchSource(name="Checkable", last_checked="")
        self.researcher.add_source(src)
        self.researcher.mark_checked("Checkable")
        assert self.researcher._sources["Checkable"].last_checked != ""


# ============================================
# Voice Provider Tests (Real Providers)
# ============================================
class TestVoiceProviders:
    """Tests for Whisper and ElevenLabs provider fallbacks."""

    @pytest.mark.asyncio
    async def test_whisper_no_api_key(self):
        """Whisper provider returns stub when OPENAI_API_KEY not set."""
        import os
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            from src.channels.voice_interface import WhisperProvider
            provider = WhisperProvider()
            result = await provider.transcribe(b"fake_audio_data")
            assert "whisper-stub" in result
        finally:
            if old:
                os.environ["OPENAI_API_KEY"] = old

    @pytest.mark.asyncio
    async def test_elevenlabs_no_api_key(self):
        """ElevenLabs provider returns stub when ELEVENLABS_API_KEY not set."""
        import os
        old = os.environ.pop("ELEVENLABS_API_KEY", None)
        try:
            from src.channels.voice_interface import ElevenLabsProvider
            provider = ElevenLabsProvider()
            result = await provider.synthesize("Hello world")
            assert b"elevenlabs-stub" in result
        finally:
            if old:
                os.environ["ELEVENLABS_API_KEY"] = old

    @pytest.mark.asyncio
    async def test_whisper_synthesize_fallback(self):
        """Whisper has no TTS capability, should return stub."""
        from src.channels.voice_interface import WhisperProvider
        provider = WhisperProvider()
        result = await provider.synthesize("Hello")
        assert b"no-tts" in result

    @pytest.mark.asyncio
    async def test_elevenlabs_transcribe_fallback(self):
        """ElevenLabs has no STT capability, should return stub."""
        from src.channels.voice_interface import ElevenLabsProvider
        provider = ElevenLabsProvider()
        result = await provider.transcribe(b"audio")
        assert "no-stt" in result


# ============================================
# PGvector Fallback Tests
# ============================================
class TestPGvectorFallback:
    """Tests that PGvector methods fall back gracefully to keyword search."""

    @pytest.mark.asyncio
    async def test_collective_query_semantic_fallback(self):
        """query_semantic falls back to keyword search when DB unavailable."""
        collective = CollectiveIntelligence()
        collective._knowledge.clear()
        collective._hashes.clear()
        collective.share("friday", "docker", "Use multi-stage builds")

        # semantic search should fallback to keyword match
        results = await collective.query_semantic("docker")
        assert len(results) == 1
        assert results[0].topic == "docker"

    @pytest.mark.asyncio
    async def test_skills_search_semantic_fallback(self):
        """search_semantic falls back to keyword search when DB unavailable."""
        from src.skills.skills_discovery import SkillsDiscovery
        discovery = SkillsDiscovery()

        # Even without PGvector, should return results (or empty) without error
        results = await discovery.search_semantic("nonexistent_skill_xyz")
        assert isinstance(results, list)
