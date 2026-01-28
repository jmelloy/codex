"""API routes for theme management."""

import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

from codex.api.schemas import ThemeResponse
from codex.plugins.loader import PluginLoader
from codex.plugins.models import ThemePlugin

router = APIRouter()


def _get_plugins_dir() -> Path:
    """Get the plugins directory path.
    
    Uses CODEX_PLUGINS_DIR environment variable if set, otherwise defaults
    to plugins/ directory at repository root (5 levels up from this file).
    """
    if plugins_dir := os.getenv("CODEX_PLUGINS_DIR"):
        return Path(plugins_dir)
    
    # Fallback: This file is at backend/codex/api/routes/themes.py
    # Repository root is 5 levels up
    return Path(__file__).parent.parent.parent.parent.parent / "plugins"


@lru_cache(maxsize=1)
def _get_plugin_loader() -> PluginLoader:
    """Get a cached plugin loader instance.
    
    Uses LRU cache to avoid reloading plugins on every request.
    Cache is invalidated when the process restarts.
    """
    loader = PluginLoader(_get_plugins_dir())
    loader.load_all_plugins()
    return loader


@router.get("", response_model=list[ThemeResponse])
async def get_available_themes():
    """Get all available themes from the plugin system.
    
    This endpoint is public (no authentication required) to allow
    theme previews before login. Theme metadata does not contain
    sensitive information.
    
    Returns:
        List of available theme plugins with their metadata.
    """
    loader = _get_plugin_loader()
    themes = loader.get_plugins_by_type("theme")
    
    # Convert theme plugins to response format
    theme_responses = []
    for theme in themes:
        if isinstance(theme, ThemePlugin):
            theme_responses.append(
                ThemeResponse(
                    id=theme.id,
                    # Use ID as name for theme identifier in frontend
                    # This is the stable identifier (e.g., "cream", "manila")
                    name=theme.id,
                    label=theme.display_name,
                    description=theme.description,
                    className=theme.class_name,
                    category=theme.category,
                    version=theme.version,
                    author=theme.author,
                )
            )
    
    return theme_responses
