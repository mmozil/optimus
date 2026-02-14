"""
Agent Optimus — Tools Manifest Generator.
Generates TOOLS.md documentation from MCP tool registry.
"""

import logging
from pathlib import Path

from src.skills.mcp_tools import mcp_tools

logger = logging.getLogger(__name__)


async def generate_tools_manifest(output_path: str | None = None) -> str:
    """Generate and optionally save TOOLS.md."""
    manifest = mcp_tools.generate_manifest()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest, encoding="utf-8")
        logger.info(f"TOOLS.md written to {output_path}")

    return manifest
