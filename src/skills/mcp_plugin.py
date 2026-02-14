"""
Agent Optimus — MCP Plugin Loader.
Dynamic loader for external MCP servers and tools.
"""

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path

from src.skills.mcp_tools import MCPTool, MCPToolRegistry, mcp_tools

logger = logging.getLogger(__name__)


@dataclass
class MCPPluginConfig:
    """Configuration for an external MCP plugin."""
    name: str
    module_path: str  # Python module path or file path
    enabled: bool = True
    config: dict | None = None
    description: str = ""


class MCPPluginLoader:
    """
    Dynamic loader for external MCP server plugins.
    Each plugin is a Python module that exports a `register_tools(registry)` function.

    Plugin structure:
    ```python
    # plugins/my_plugin.py
    from src.skills.mcp_tools import MCPTool, MCPToolRegistry

    async def my_handler(param1: str) -> str:
        return "result"

    def register_tools(registry: MCPToolRegistry):
        registry.register(MCPTool(
            name="my_tool",
            description="My custom tool",
            category="custom",
            handler=my_handler,
        ))
    ```
    """

    def __init__(self, registry: MCPToolRegistry | None = None):
        self._registry = registry or mcp_tools
        self._loaded_plugins: dict[str, MCPPluginConfig] = {}

    async def load_plugin(self, config: MCPPluginConfig) -> bool:
        """Load a single MCP plugin."""
        if not config.enabled:
            logger.debug(f"Plugin '{config.name}' is disabled, skipping")
            return False

        try:
            # Try importing as module
            module = importlib.import_module(config.module_path)

            # Call register_tools function
            register_fn = getattr(module, "register_tools", None)
            if register_fn:
                register_fn(self._registry)
                self._loaded_plugins[config.name] = config
                logger.info(f"Plugin loaded: {config.name} ({config.module_path})")
                return True
            else:
                logger.warning(f"Plugin '{config.name}' has no register_tools function")
                return False

        except ImportError as e:
            logger.error(f"Plugin '{config.name}' import failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Plugin '{config.name}' loading failed: {e}")
            return False

    async def load_from_directory(self, plugins_dir: str) -> int:
        """Load all plugins from a directory."""
        path = Path(plugins_dir)
        if not path.exists():
            logger.debug(f"Plugins directory '{plugins_dir}' not found")
            return 0

        loaded = 0
        for py_file in sorted(path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            config = MCPPluginConfig(
                name=py_file.stem,
                module_path=str(py_file),
                description=f"Auto-loaded from {plugins_dir}",
            )

            # For file-based loading
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    register_fn = getattr(module, "register_tools", None)
                    if register_fn:
                        register_fn(self._registry)
                        self._loaded_plugins[config.name] = config
                        loaded += 1
                        logger.info(f"Plugin loaded from file: {py_file.name}")

            except Exception as e:
                logger.error(f"Failed to load plugin file {py_file.name}: {e}")

        logger.info(f"Loaded {loaded} plugins from {plugins_dir}")
        return loaded

    async def load_configs(self, configs: list[MCPPluginConfig]) -> int:
        """Load multiple plugin configurations."""
        loaded = 0
        for config in configs:
            if await self.load_plugin(config):
                loaded += 1
        return loaded

    def list_plugins(self) -> list[dict]:
        """List loaded plugins."""
        return [
            {"name": c.name, "module": c.module_path, "description": c.description}
            for c in self._loaded_plugins.values()
        ]

    def is_loaded(self, name: str) -> bool:
        return name in self._loaded_plugins


# Singleton
mcp_plugin_loader = MCPPluginLoader()
