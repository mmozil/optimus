"""
Tests for agent system — Base Agent, Factory, Personas.
"""

import pytest

from src.agents.base import AgentConfig, BaseAgent
from src.core.agent_factory import AgentFactory
from src.identity.personas import PersonaSelector
from src.identity.soul_loader import SoulLoader


# ============================================
# SoulLoader Tests
# ============================================
class TestSoulLoader:
    def setup_method(self):
        SoulLoader.clear_cache()

    def test_load_existing_soul(self, tmp_path):
        soul_file = tmp_path / "test.md"
        soul_file.write_text("# Test Agent\nVocê é um agente de teste.", encoding="utf-8")

        content = SoulLoader.load(str(soul_file))
        assert "Test Agent" in content
        assert "agente de teste" in content

    def test_load_missing_soul_returns_empty(self):
        content = SoulLoader.load("/nonexistent/path.md")
        assert content == ""

    def test_cache_works(self, tmp_path):
        soul_file = tmp_path / "cached.md"
        soul_file.write_text("Original", encoding="utf-8")

        first = SoulLoader.load(str(soul_file))
        soul_file.write_text("Modified", encoding="utf-8")
        second = SoulLoader.load(str(soul_file))

        assert first == second == "Original"

    def test_reload_clears_cache(self, tmp_path):
        soul_file = tmp_path / "reload.md"
        soul_file.write_text("Original", encoding="utf-8")
        SoulLoader.load(str(soul_file))

        soul_file.write_text("Modified", encoding="utf-8")
        content = SoulLoader.reload(str(soul_file))

        assert content == "Modified"

    def test_load_section(self, tmp_path):
        soul_file = tmp_path / "sections.md"
        soul_file.write_text(
            "# Agent\n## Personalidade\nAmigável\n## Regras\nSer preciso",
            encoding="utf-8",
        )

        personality = SoulLoader.load_section(str(soul_file), "Personalidade")
        assert "Amigável" in personality
        assert "Ser preciso" not in personality


# ============================================
# PersonaSelector Tests
# ============================================
class TestPersonaSelector:
    def test_classify_debug_intent(self):
        intent = PersonaSelector.classify_intent("Tem um bug no traceback do sistema")
        assert intent == "debug"

    def test_classify_alert_intent(self):
        intent = PersonaSelector.classify_intent("Urgente! Erro 429 no servidor")
        assert intent == "alert"

    def test_classify_analysis_intent(self):
        intent = PersonaSelector.classify_intent("Faça uma análise comparativa dos dados")
        assert intent == "analysis"

    def test_classify_default_intent(self):
        intent = PersonaSelector.classify_intent("Olá, tudo bem?")
        assert intent == "default"

    def test_get_persona_returns_dict(self):
        persona = PersonaSelector.get_persona("debug")
        assert "name" in persona
        assert "style" in persona
        assert "temperature" in persona
        assert persona["name"] == "Debugger"

    def test_get_persona_prompt(self):
        prompt = PersonaSelector.get_persona_prompt("Analise os dados")
        assert "Modo Atual" in prompt


# ============================================
# AgentConfig Tests
# ============================================
class TestAgentConfig:
    def test_default_values(self):
        config = AgentConfig(name="test", role="Tester")
        assert config.level == "specialist"
        assert config.model == "gemini-2.5-flash"
        assert config.temperature == 0.7

    def test_custom_values(self):
        config = AgentConfig(
            name="boss",
            role="Lead",
            level="lead",
            model="gemini-2.5-pro",
            temperature=0.9,
        )
        assert config.level == "lead"
        assert config.model == "gemini-2.5-pro"


# ============================================
# BaseAgent Tests
# ============================================
class TestBaseAgent:
    def test_agent_creation(self):
        config = AgentConfig(name="tester", role="Test Agent")
        agent = BaseAgent(config=config)

        assert agent.name == "tester"
        assert agent.role == "Test Agent"
        assert agent.level == "specialist"

    def test_system_prompt_includes_soul(self):
        config = AgentConfig(name="tester", role="Test", soul_md="Amigável e prestativo.")
        agent = BaseAgent(config=config)

        assert "Amigável" in agent._system_prompt
        assert "tester" in agent._system_prompt

    def test_repr(self):
        config = AgentConfig(name="tester", role="Test")
        agent = BaseAgent(config=config)

        assert "tester" in repr(agent)
        assert "Test" in repr(agent)


# ============================================
# AgentFactory Tests
# ============================================
class TestAgentFactory:
    def setup_method(self):
        AgentFactory.clear()

    def test_create_and_get(self):
        agent = AgentFactory.create(
            name="factory_test",
            role="Test Agent",
            soul_content="Soul de teste.",
        )
        assert agent.name == "factory_test"

        retrieved = AgentFactory.get("factory_test")
        assert retrieved is agent

    def test_list_agents(self):
        AgentFactory.create(name="a1", role="R1", soul_content="Soul 1")
        AgentFactory.create(name="a2", role="R2", soul_content="Soul 2")

        agents = AgentFactory.list_agents()
        assert len(agents) == 2
        names = [a["name"] for a in agents]
        assert "a1" in names
        assert "a2" in names

    def test_remove_agent(self):
        AgentFactory.create(name="removable", role="Test", soul_content="")
        assert AgentFactory.get("removable") is not None

        result = AgentFactory.remove("removable")
        assert result is True
        assert AgentFactory.get("removable") is None

    def test_remove_nonexistent(self):
        result = AgentFactory.remove("ghost")
        assert result is False
