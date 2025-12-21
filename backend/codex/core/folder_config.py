"""Folder-level configuration system for Codex.

This module provides support for `.` directories that contain
configuration files and properties at each folder level.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from codex.core.markdown import MarkdownDocument, parse_markdown_file


class FolderConfig:
    """Configuration for a folder."""

    def __init__(self, folder_path: Path):
        """Initialize folder configuration.

        Args:
            folder_path: Path to the folder
        """
        self.folder_path = Path(folder_path)
        self.config_dir = self.folder_path / "."
        self.agents_file = self.config_dir / "agents.md"
        self.properties_file = self.config_dir / "properties.md"
        self._agents_config: Optional[MarkdownDocument] = None
        self._properties: Optional[MarkdownDocument] = None
        self._parent_config: Optional["FolderConfig"] = None

    @property
    def agents_config(self) -> Optional[MarkdownDocument]:
        """Get agents configuration.

        Returns:
            MarkdownDocument or None if file doesn't exist
        """
        if self._agents_config is None and self.agents_file.exists():
            self._agents_config = parse_markdown_file(str(self.agents_file))
        return self._agents_config

    @property
    def properties(self) -> Optional[MarkdownDocument]:
        """Get properties configuration.

        Returns:
            MarkdownDocument or None if file doesn't exist
        """
        if self._properties is None and self.properties_file.exists():
            self._properties = parse_markdown_file(str(self.properties_file))
        return self._properties

    @property
    def parent_config(self) -> Optional["FolderConfig"]:
        """Get parent folder configuration.

        Returns:
            FolderConfig for parent or None
        """
        if self._parent_config is None:
            parent_path = self.folder_path.parent
            if parent_path != self.folder_path and parent_path.exists():
                self._parent_config = FolderConfig(parent_path)
        return self._parent_config

    def get_property(self, key: str, default: Any = None, inherit: bool = True) -> Any:
        """Get a property value.

        Args:
            key: Property key
            default: Default value if not found
            inherit: Whether to check parent configurations

        Returns:
            Property value
        """
        # Check local properties first
        if self.properties:
            value = self.properties.get_frontmatter(key)
            if value is not None:
                return value

        # Check parent if inheritance is enabled
        if inherit and self.parent_config:
            return self.parent_config.get_property(key, default, inherit=True)

        return default

    def set_property(self, key: str, value: Any) -> None:
        """Set a property value.

        Args:
            key: Property key
            value: Property value
        """
        if self._properties is None:
            self._properties = MarkdownDocument()

        self._properties.set_frontmatter(key, value)
        self._save_properties()

    def get_agent_config(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get agent configuration.

        Args:
            agent_name: Optional specific agent name

        Returns:
            Agent configuration dictionary
        """
        config = {}

        # Inherit from parent first
        if self.parent_config:
            config = self.parent_config.get_agent_config(agent_name)

        # Override with local configuration
        if self.agents_config:
            local_config = self.agents_config.frontmatter.copy()
            if agent_name and agent_name in local_config:
                config.update(local_config[agent_name])
            else:
                config.update(local_config)

        return config

    def set_agent_config(self, config: Dict[str, Any], agent_name: Optional[str] = None) -> None:
        """Set agent configuration.

        Args:
            config: Configuration dictionary
            agent_name: Optional specific agent name
        """
        if self._agents_config is None:
            self._agents_config = MarkdownDocument()

        if agent_name:
            # Set configuration for specific agent
            self._agents_config.set_frontmatter(agent_name, config)
        else:
            # Update global agent configuration
            for key, value in config.items():
                self._agents_config.set_frontmatter(key, value)

        self._save_agents_config()

    def get_agent_instructions(self, agent_name: Optional[str] = None) -> Optional[str]:
        """Get agent instructions from markdown content.

        Args:
            agent_name: Optional specific agent name

        Returns:
            Instructions text or None
        """
        if not self.agents_config:
            return None

        if agent_name:
            # Look for specific agent block
            block = self.agents_config.get_block(agent_name)
            if block:
                return block

        # Return main content as default instructions
        return self.agents_config.content if self.agents_config.content else None

    def add_agent_instructions(self, instructions: str, agent_name: Optional[str] = None) -> None:
        """Add agent instructions.

        Args:
            instructions: Instructions text
            agent_name: Optional specific agent name (creates a block)
        """
        if self._agents_config is None:
            self._agents_config = MarkdownDocument()

        if agent_name:
            # Add as a named block
            self._agents_config.add_block(agent_name, instructions)
        else:
            # Add to main content
            self._agents_config.content = instructions

        self._save_agents_config()

    def ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_dir.mkdir(exist_ok=True)

    def _save_properties(self) -> None:
        """Save properties to disk."""
        self.ensure_config_dir()
        if self._properties:
            with open(self.properties_file, "w") as f:
                f.write(self._properties.to_markdown())

    def _save_agents_config(self) -> None:
        """Save agents configuration to disk."""
        self.ensure_config_dir()
        if self._agents_config:
            with open(self.agents_file, "w") as f:
                f.write(self._agents_config.to_markdown())

    def list_agents(self) -> List[str]:
        """List all configured agents.

        Returns:
            List of agent names
        """
        agents = set()

        # Add from parent
        if self.parent_config:
            agents.update(self.parent_config.list_agents())

        # Add from local config
        if self.agents_config:
            # Add agents from frontmatter
            for key in self.agents_config.frontmatter.keys():
                if isinstance(self.agents_config.frontmatter[key], dict):
                    agents.add(key)

            # Add agents from blocks
            for block in self.agents_config.blocks:
                agents.add(block["type"])

        return sorted(list(agents))


class ConfigManager:
    """Manager for folder configurations."""

    def __init__(self, root_path: Path):
        """Initialize configuration manager.

        Args:
            root_path: Root path for configurations
        """
        self.root_path = Path(root_path)
        self._configs: Dict[str, FolderConfig] = {}

    def get_config(self, folder_path: Path) -> FolderConfig:
        """Get configuration for a folder.

        Args:
            folder_path: Path to folder

        Returns:
            FolderConfig instance
        """
        folder_path = Path(folder_path).resolve()
        path_str = str(folder_path)

        if path_str not in self._configs:
            self._configs[path_str] = FolderConfig(folder_path)

        return self._configs[path_str]

    def find_config_file(self, start_path: Path, filename: str) -> Optional[Path]:
        """Find a configuration file by walking up the directory tree.

        Args:
            start_path: Starting path
            filename: Name of file to find

        Returns:
            Path to file or None if not found
        """
        current = Path(start_path).resolve()

        while current != current.parent:
            config_file = current / "." / filename
            if config_file.exists():
                return config_file
            current = current.parent

        return None

    def get_effective_config(self, folder_path: Path) -> Dict[str, Any]:
        """Get effective configuration for a folder (with inheritance).

        Args:
            folder_path: Path to folder

        Returns:
            Dictionary of all effective properties
        """
        config = self.get_config(folder_path)
        effective = {}

        # Collect all properties from root to this folder
        current = config
        hierarchy = []
        while current is not None:
            hierarchy.append(current)
            current = current.parent_config

        # Apply from root down (so child overrides parent)
        for cfg in reversed(hierarchy):
            if cfg.properties:
                effective.update(cfg.properties.frontmatter)

        return effective
