"""Tests for folder configuration system."""

import tempfile
from pathlib import Path

import pytest

from core.folder_config import ConfigManager, FolderConfig
from core.markdown import MarkdownDocument


class TestFolderConfig:
    """Test FolderConfig class."""

    def test_create_folder_config(self):
        """Test creating a folder configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)
            assert config.folder_path == folder
            assert config.config_dir == folder / "."

    def test_get_property_no_file(self):
        """Test getting property when no properties file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)
            assert config.get_property("key") is None
            assert config.get_property("key", "default") == "default"

    def test_set_and_get_property(self):
        """Test setting and getting a property."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            config.set_property("name", "Test")
            config.set_property("count", 42)

            assert config.get_property("name") == "Test"
            assert config.get_property("count") == 42

    def test_property_persistence(self):
        """Test that properties are persisted to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()

            # Set properties
            config1 = FolderConfig(folder)
            config1.set_property("key", "value")

            # Load in new instance
            config2 = FolderConfig(folder)
            assert config2.get_property("key") == "value"

    def test_property_inheritance(self):
        """Test property inheritance from parent folders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()

            # Set property in parent
            parent_config = FolderConfig(parent)
            parent_config.set_property("inherited", "from_parent")
            parent_config.set_property("color", "blue")

            # Set property in child
            child_config = FolderConfig(child)
            child_config.set_property("color", "red")

            # Child should inherit from parent
            assert child_config.get_property("inherited") == "from_parent"
            # Child should override parent
            assert child_config.get_property("color") == "red"

    def test_property_no_inheritance(self):
        """Test getting property without inheritance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()

            parent_config = FolderConfig(parent)
            parent_config.set_property("key", "parent_value")

            child_config = FolderConfig(child)
            # Should not find parent value when inherit=False
            assert child_config.get_property("key", inherit=False) is None

    def test_set_and_get_agent_config(self):
        """Test setting and getting agent configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            agent_cfg = {"model": "gpt-4", "temperature": 0.7}
            config.set_agent_config(agent_cfg)

            retrieved = config.get_agent_config()
            assert retrieved["model"] == "gpt-4"
            assert retrieved["temperature"] == 0.7

    def test_named_agent_config(self):
        """Test configuration for a named agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            # Set config for specific agent
            config.set_agent_config({"model": "claude-3"}, agent_name="analyzer")

            # Get config for that agent
            analyzer_cfg = config.get_agent_config("analyzer")
            assert analyzer_cfg["model"] == "claude-3"

    def test_agent_config_inheritance(self):
        """Test agent configuration inheritance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()

            # Set global config in parent
            parent_config = FolderConfig(parent)
            parent_config.set_agent_config({"model": "gpt-4", "temperature": 0.5})

            # Override in child
            child_config = FolderConfig(child)
            child_config.set_agent_config({"temperature": 0.9})

            # Child should inherit model but override temperature
            cfg = child_config.get_agent_config()
            assert cfg["model"] == "gpt-4"
            assert cfg["temperature"] == 0.9

    def test_get_agent_instructions(self):
        """Test getting agent instructions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            instructions = "These are the agent instructions."
            config.add_agent_instructions(instructions)

            retrieved = config.get_agent_instructions()
            assert instructions in retrieved

    def test_named_agent_instructions(self):
        """Test getting instructions for a named agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            config.add_agent_instructions(
                "Analyzer instructions", agent_name="analyzer"
            )
            config.add_agent_instructions("Writer instructions", agent_name="writer")

            analyzer_instr = config.get_agent_instructions("analyzer")
            writer_instr = config.get_agent_instructions("writer")

            assert "Analyzer" in analyzer_instr
            assert "Writer" in writer_instr

    def test_list_agents_empty(self):
        """Test listing agents when none configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            agents = config.list_agents()
            assert agents == []

    def test_list_agents(self):
        """Test listing configured agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            config.set_agent_config({"model": "gpt-4"}, agent_name="analyzer")
            config.set_agent_config({"model": "claude"}, agent_name="writer")
            config.add_agent_instructions("Instructions", agent_name="reviewer")

            agents = config.list_agents()
            assert "analyzer" in agents
            assert "writer" in agents
            assert "reviewer" in agents

    def test_list_agents_with_inheritance(self):
        """Test listing agents includes parent agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()

            parent_config = FolderConfig(parent)
            parent_config.set_agent_config(
                {"model": "gpt-4"}, agent_name="parent_agent"
            )

            child_config = FolderConfig(child)
            child_config.set_agent_config({"model": "claude"}, agent_name="child_agent")

            agents = child_config.list_agents()
            assert "parent_agent" in agents
            assert "child_agent" in agents

    def test_ensure_config_dir(self):
        """Test ensuring config directory exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()
            config = FolderConfig(folder)

            config.ensure_config_dir()
            assert config.config_dir.exists()
            assert config.config_dir.is_dir()


class TestConfigManager:
    """Test ConfigManager class."""

    def test_create_config_manager(self):
        """Test creating a configuration manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigManager(Path(tmpdir))
            assert manager.root_path == Path(tmpdir)

    def test_get_config(self):
        """Test getting configuration for a folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()

            manager = ConfigManager(Path(tmpdir))
            config = manager.get_config(folder)

            assert isinstance(config, FolderConfig)
            assert config.folder_path == folder

    def test_get_config_caching(self):
        """Test that configs are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()

            manager = ConfigManager(Path(tmpdir))
            config1 = manager.get_config(folder)
            config2 = manager.get_config(folder)

            # Should return same instance
            assert config1 is config2

    def test_find_config_file_exists(self):
        """Test finding a configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()

            # Create config in parent
            parent_config_dir = parent / "."
            parent_config_dir.mkdir(exist_ok=True)
            agents_file = parent_config_dir / "agents.md"
            agents_file.write_text("# Agent config")

            manager = ConfigManager(root)
            found = manager.find_config_file(child, "agents.md")

            assert found is not None
            assert found == agents_file

    def test_find_config_file_not_exists(self):
        """Test finding a config file that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()

            manager = ConfigManager(Path(tmpdir))
            found = manager.find_config_file(folder, "nonexistent.md")

            assert found is None

    def test_get_effective_config(self):
        """Test getting effective configuration with inheritance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent"
            child = parent / "child"
            parent.mkdir()
            child.mkdir()

            # Set properties at different levels
            parent_config = FolderConfig(parent)
            parent_config.set_property("color", "blue")
            parent_config.set_property("size", "large")

            child_config = FolderConfig(child)
            child_config.set_property("color", "red")
            child_config.set_property("shape", "circle")

            # Get effective config
            manager = ConfigManager(root)
            effective = manager.get_effective_config(child)

            # Should have child override and both parent and child properties
            assert effective["color"] == "red"  # Overridden
            assert effective["size"] == "large"  # Inherited
            assert effective["shape"] == "circle"  # Child only

    def test_get_effective_config_empty(self):
        """Test getting effective config when no properties set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir) / "test_folder"
            folder.mkdir()

            manager = ConfigManager(Path(tmpdir))
            effective = manager.get_effective_config(folder)

            assert effective == {}
