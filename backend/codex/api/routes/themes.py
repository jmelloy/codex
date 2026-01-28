"""API routes for theme management."""

from fastapi import APIRouter, Request

from codex.api.schemas import ThemeResponse
from codex.plugins.models import ThemePlugin

router = APIRouter()


@router.get("", response_model=list[ThemeResponse])
async def get_available_themes(request: Request):
    """Get all available themes from the plugin system.
    
    This endpoint is public (no authentication required) to allow
    theme previews before login. Theme metadata does not contain
    sensitive information.
    
    Returns:
        List of available theme plugins with their metadata.
    """
    loader = request.app.state.plugin_loader
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
