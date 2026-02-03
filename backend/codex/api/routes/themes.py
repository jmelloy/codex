"""API routes for theme management."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class ThemeResponse(BaseModel):
    """Schema for theme information."""

    id: str
    name: str
    label: str
    description: str
    className: str
    category: str
    version: str
    author: str


@router.get("", response_model=list[ThemeResponse])
async def list_themes(request: Request):
    """List all available themes.

    Returns:
        List of available themes
    """
    # Get the plugin loader from app state
    plugin_loader = request.app.state.plugin_loader
    
    # Get all theme plugins
    themes = plugin_loader.get_plugins_by_type("theme")
    
    # Transform to response format
    result = []
    for theme in themes:
        # Get theme configuration from manifest
        theme_config = theme.manifest.get("theme", {})
        
        result.append(
            ThemeResponse(
                id=theme.id,
                name=theme.name,
                label=theme_config.get("display_name", theme.name),
                description=theme.description or "",
                className=theme_config.get("className", f"theme-{theme.id}"),
                category=theme_config.get("category", "light"),
                version=theme.version,
                author=theme.author or "Unknown",
            )
        )
    
    return result
