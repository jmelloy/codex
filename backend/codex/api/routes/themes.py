"""API routes for theme management."""

from pathlib import Path

from fastapi import APIRouter

from codex.api.schemas import ThemeResponse
from codex.plugins.loader import PluginLoader
from codex.plugins.models import ThemePlugin

router = APIRouter()

# Get the plugins directory relative to the repository root
# This file is at backend/codex/api/routes/themes.py
# Plugins are at plugins/ (repository root)
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"


@router.get("", response_model=list[ThemeResponse])
async def get_available_themes():
    """Get all available themes from the plugin system.
    
    Returns:
        List of available theme plugins with their metadata.
    """
    loader = PluginLoader(PLUGINS_DIR)
    loader.load_all_plugins()
    
    themes = loader.get_plugins_by_type("theme")
    
    # Convert theme plugins to response format
    theme_responses = []
    for theme in themes:
        if isinstance(theme, ThemePlugin):
            theme_responses.append(
                ThemeResponse(
                    id=theme.id,
                    name=theme.id,  # Use ID as name for backwards compatibility
                    label=theme.display_name,
                    description=theme.description,
                    className=theme.class_name,
                    category=theme.category,
                    version=theme.version,
                    author=theme.author,
                )
            )
    
    return theme_responses
