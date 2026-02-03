"""Tests for plugin enable/disable functionality at workspace and notebook levels."""

import pytest
from sqlmodel import select

from codex.db.database import get_system_session
from codex.db.models import (
    Notebook,
    NotebookPluginConfig,
    Plugin,
    PluginConfig,
    User,
    Workspace,
)


@pytest.fixture
async def session():
    """Create a database session for tests."""
    async for sess in get_system_session():
        yield sess


@pytest.fixture
async def test_user(session):
    """Create a test user."""
    import time
    
    username = f"testuser_{int(time.time() * 1000)}"
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed_password",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def test_workspace(session, test_user):
    """Create a test workspace."""
    import time
    
    workspace = Workspace(
        name="Test Workspace",
        slug="test-workspace",
        path=f"/tmp/test-workspace-{int(time.time() * 1000)}",
        owner_id=test_user.id,
    )
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace


@pytest.fixture
async def test_notebook(session, test_workspace):
    """Create a test notebook."""
    notebook = Notebook(
        workspace_id=test_workspace.id,
        name="Test Notebook",
        slug="test-notebook",
        path="test-notebook",
    )
    session.add(notebook)
    await session.commit()
    await session.refresh(notebook)
    return notebook


@pytest.fixture
async def test_plugin(session):
    """Create a test plugin."""
    import time
    
    plugin_id = f"test-plugin-{int(time.time() * 1000)}"
    plugin = Plugin(
        plugin_id=plugin_id,
        name="Test Plugin",
        version="1.0.0",
        type="integration",
        enabled=True,
        manifest={"id": plugin_id, "name": "Test Plugin", "version": "1.0.0", "type": "integration"},
    )
    session.add(plugin)
    await session.commit()
    await session.refresh(plugin)
    return plugin


@pytest.mark.asyncio
async def test_workspace_plugin_config_enabled_default(
    session,
    test_workspace: Workspace,
    test_plugin: Plugin,
):
    """Test that workspace plugin config defaults to enabled."""
    config = PluginConfig(
        workspace_id=test_workspace.id,
        plugin_id=test_plugin.plugin_id,
        config={},
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    assert config.enabled is True


@pytest.mark.asyncio
async def test_workspace_plugin_disable(
    session,
    test_workspace: Workspace,
    test_plugin: Plugin,
):
    """Test disabling a plugin at workspace level."""
    config = PluginConfig(
        workspace_id=test_workspace.id,
        plugin_id=test_plugin.plugin_id,
        enabled=False,
        config={},
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    assert config.enabled is False
    
    # Query and verify
    stmt = select(PluginConfig).where(
        PluginConfig.workspace_id == test_workspace.id,
        PluginConfig.plugin_id == test_plugin.plugin_id,
    )
    result = await session.execute(stmt)
    retrieved = result.scalar_one_or_none()
    
    assert retrieved is not None
    assert retrieved.enabled is False


@pytest.mark.asyncio
async def test_workspace_plugin_enable_after_disable(
    session,
    test_workspace: Workspace,
    test_plugin: Plugin,
):
    """Test re-enabling a disabled plugin at workspace level."""
    config = PluginConfig(
        workspace_id=test_workspace.id,
        plugin_id=test_plugin.plugin_id,
        enabled=False,
        config={},
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    assert config.enabled is False
    
    # Re-enable
    config.enabled = True
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    assert config.enabled is True


@pytest.mark.asyncio
async def test_notebook_plugin_config_creation(
    session,
    test_notebook: Notebook,
    test_plugin: Plugin,
):
    """Test creating notebook plugin config."""
    config = NotebookPluginConfig(
        notebook_id=test_notebook.id,
        plugin_id=test_plugin.plugin_id,
        enabled=True,
        config={"key": "value"},
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    assert config.id is not None
    assert config.notebook_id == test_notebook.id
    assert config.plugin_id == test_plugin.plugin_id
    assert config.enabled is True
    assert config.config == {"key": "value"}


@pytest.mark.asyncio
async def test_notebook_plugin_disable_override(
    session,
    test_workspace: Workspace,
    test_notebook: Notebook,
    test_plugin: Plugin,
):
    """Test notebook-level plugin disable overrides workspace setting."""
    # Enable at workspace level
    workspace_config = PluginConfig(
        workspace_id=test_workspace.id,
        plugin_id=test_plugin.plugin_id,
        enabled=True,
        config={},
    )
    session.add(workspace_config)
    await session.commit()
    
    # Disable at notebook level
    notebook_config = NotebookPluginConfig(
        notebook_id=test_notebook.id,
        plugin_id=test_plugin.plugin_id,
        enabled=False,
        config={},
    )
    session.add(notebook_config)
    await session.commit()
    await session.refresh(notebook_config)
    
    # Verify notebook override
    assert workspace_config.enabled is True
    assert notebook_config.enabled is False


@pytest.mark.asyncio
async def test_notebook_plugin_enable_when_workspace_disabled(
    session,
    test_workspace: Workspace,
    test_notebook: Notebook,
    test_plugin: Plugin,
):
    """Test notebook can enable plugin even when disabled at workspace level."""
    # Disable at workspace level
    workspace_config = PluginConfig(
        workspace_id=test_workspace.id,
        plugin_id=test_plugin.plugin_id,
        enabled=False,
        config={},
    )
    session.add(workspace_config)
    await session.commit()
    
    # Enable at notebook level
    notebook_config = NotebookPluginConfig(
        notebook_id=test_notebook.id,
        plugin_id=test_plugin.plugin_id,
        enabled=True,
        config={},
    )
    session.add(notebook_config)
    await session.commit()
    await session.refresh(notebook_config)
    
    # Verify notebook override
    assert workspace_config.enabled is False
    assert notebook_config.enabled is True


@pytest.mark.asyncio
async def test_multiple_notebook_plugin_configs(
    session,
    test_workspace: Workspace,
    test_plugin: Plugin,
):
    """Test multiple notebooks with different plugin configs."""
    # Create two notebooks
    notebook1 = Notebook(
        workspace_id=test_workspace.id,
        name="Notebook 1",
        path="notebook-1",
    )
    notebook2 = Notebook(
        workspace_id=test_workspace.id,
        name="Notebook 2",
        path="notebook-2",
    )
    session.add(notebook1)
    session.add(notebook2)
    await session.commit()
    await session.refresh(notebook1)
    await session.refresh(notebook2)
    
    # Enable plugin in notebook1, disable in notebook2
    config1 = NotebookPluginConfig(
        notebook_id=notebook1.id,
        plugin_id=test_plugin.plugin_id,
        enabled=True,
        config={},
    )
    config2 = NotebookPluginConfig(
        notebook_id=notebook2.id,
        plugin_id=test_plugin.plugin_id,
        enabled=False,
        config={},
    )
    session.add(config1)
    session.add(config2)
    await session.commit()
    
    # Verify each config
    stmt1 = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook1.id,
        NotebookPluginConfig.plugin_id == test_plugin.plugin_id,
    )
    result1 = await session.execute(stmt1)
    retrieved1 = result1.scalar_one_or_none()
    
    stmt2 = select(NotebookPluginConfig).where(
        NotebookPluginConfig.notebook_id == notebook2.id,
        NotebookPluginConfig.plugin_id == test_plugin.plugin_id,
    )
    result2 = await session.execute(stmt2)
    retrieved2 = result2.scalar_one_or_none()
    
    assert retrieved1 is not None
    assert retrieved1.enabled is True
    assert retrieved2 is not None
    assert retrieved2.enabled is False


@pytest.mark.asyncio
async def test_notebook_plugin_config_with_custom_settings(
    session,
    test_notebook: Notebook,
    test_plugin: Plugin,
):
    """Test notebook plugin config with custom configuration."""
    custom_config = {
        "api_key": "test-key",
        "endpoint": "https://api.example.com",
        "timeout": 30,
    }
    
    config = NotebookPluginConfig(
        notebook_id=test_notebook.id,
        plugin_id=test_plugin.plugin_id,
        enabled=True,
        config=custom_config,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    assert config.config == custom_config
    assert config.config["api_key"] == "test-key"
    assert config.config["endpoint"] == "https://api.example.com"
    assert config.config["timeout"] == 30


@pytest.mark.asyncio
async def test_delete_notebook_plugin_config(
    session,
    test_notebook: Notebook,
    test_plugin: Plugin,
):
    """Test deleting notebook plugin config."""
    config = NotebookPluginConfig(
        notebook_id=test_notebook.id,
        plugin_id=test_plugin.plugin_id,
        enabled=False,
        config={},
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    
    config_id = config.id
    
    # Delete config
    await session.delete(config)
    await session.commit()
    
    # Verify deletion
    stmt = select(NotebookPluginConfig).where(
        NotebookPluginConfig.id == config_id
    )
    result = await session.execute(stmt)
    retrieved = result.scalar_one_or_none()
    
    assert retrieved is None
