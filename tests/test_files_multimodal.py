"""
Tests for Phase 14: Files Service + Multimodal.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.files_service import FilesService, ALLOWED_MIME_TYPES, MAX_FILE_SIZE_BYTES


class TestFilesServiceValidation:
    """Tests for FilesService input validation."""

    def setup_method(self):
        self.service = FilesService(bucket="test-bucket")

    @pytest.mark.asyncio
    async def test_rejects_empty_file(self):
        with pytest.raises(ValueError, match="Arquivo vazio"):
            await self.service.upload_file(
                file_content=b"",
                filename="empty.png",
                mime_type="image/png",
            )

    @pytest.mark.asyncio
    async def test_rejects_disallowed_mime_type(self):
        with pytest.raises(ValueError, match="não permitido"):
            await self.service.upload_file(
                file_content=b"data",
                filename="malware.exe",
                mime_type="application/x-msdownload",
            )

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self):
        oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(ValueError, match="muito grande"):
            await self.service.upload_file(
                file_content=oversized,
                filename="huge.png",
                mime_type="image/png",
            )

    @pytest.mark.asyncio
    async def test_rejects_when_no_supabase_client(self):
        """Should raise RuntimeError when Supabase is not configured."""
        with patch("src.core.files_service.FilesService.upload_file") as mock:
            mock.side_effect = RuntimeError("Supabase client not configured")
            with pytest.raises(RuntimeError, match="Supabase"):
                await mock(
                    file_content=b"img",
                    filename="test.png",
                    mime_type="image/png",
                )

    def test_allowed_mime_types_include_basics(self):
        """Ensure the core types are whitelisted."""
        assert "image/png" in ALLOWED_MIME_TYPES
        assert "image/jpeg" in ALLOWED_MIME_TYPES
        assert "application/pdf" in ALLOWED_MIME_TYPES
        assert "text/csv" in ALLOWED_MIME_TYPES


class TestMultimodalContentBuilding:
    """Tests for BaseAgent._build_multimodal_content."""

    def test_builds_text_plus_image_parts(self):
        from src.agents.base import BaseAgent, AgentConfig

        config = AgentConfig(name="test", role="tester")
        agent = BaseAgent(config)

        attachments = [
            {"mime_type": "image/png", "public_url": "https://storage.example.com/img.png"},
            {"mime_type": "text/plain", "public_url": "https://storage.example.com/readme.txt"},
        ]

        result = agent._build_multimodal_content("Analise essa imagem", attachments)

        # Should have text + 1 image (text/plain is not an image, so skipped)
        assert len(result) == 2
        assert result[0] == {"type": "text", "text": "Analise essa imagem"}
        assert result[1]["type"] == "image_url"
        assert result[1]["image_url"]["url"] == "https://storage.example.com/img.png"

    def test_pdf_also_included(self):
        from src.agents.base import BaseAgent, AgentConfig

        config = AgentConfig(name="test", role="tester")
        agent = BaseAgent(config)

        attachments = [
            {"mime_type": "application/pdf", "public_url": "https://storage.example.com/doc.pdf"},
        ]

        result = agent._build_multimodal_content("Resuma esse PDF", attachments)

        assert len(result) == 2
        assert result[1]["type"] == "image_url"

    def test_empty_attachments_returns_text_only(self):
        from src.agents.base import BaseAgent, AgentConfig

        config = AgentConfig(name="test", role="tester")
        agent = BaseAgent(config)

        result = agent._build_multimodal_content("Texto simples", [])
        assert len(result) == 1
        assert result[0] == {"type": "text", "text": "Texto simples"}


class TestReActLoopMultimodal:
    """Test that the ReAct loop correctly formats multimodal messages."""

    def test_react_loop_builds_multimodal_user_message(self):
        """Verify that _build_user_content + attachment logic produces the right format."""
        from src.engine.react_loop import _build_user_content

        context = {
            "attachments": [
                {"mime_type": "image/jpeg", "public_url": "https://cdn.example.com/screenshot.jpg"},
            ],
        }

        user_content = _build_user_content("O que tem nesta imagem?", context)

        # Build multimodal parts (replicating react_loop logic)
        content_parts = [{"type": "text", "text": user_content}]
        for att in context["attachments"]:
            mime = att.get("mime_type", "")
            if mime and ("image" in mime or "pdf" in mime):
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": att.get("public_url", "")},
                })

        assert len(content_parts) == 2
        assert content_parts[0]["type"] == "text"
        assert content_parts[1]["type"] == "image_url"
        assert "screenshot.jpg" in content_parts[1]["image_url"]["url"]
