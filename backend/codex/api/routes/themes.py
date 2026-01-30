"""API routes for theme management."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from codex.api.schemas import ThemeResponse

router = APIRouter()


@router.get("", response_model=list[ThemeResponse])
async def get_available_themes(request: Request):
    """Get all available themes from the plugin system.
    
    This endpoint is public (no authentication required) to allow
    theme previews before login. Theme metadata does not contain
    sensitive information.
    
    Returns all plugins that provide themes, regardless of plugin type.
    This allows any plugin (view, theme, integration) to expose themes.
    
    Returns:
        List of available theme plugins with their metadata.
    """
    loader = request.app.state.plugin_loader
    # Use capability-based filtering instead of type-based
    plugins_with_themes = loader.get_plugins_with_themes()
    
    # Convert plugins with themes to response format
    theme_responses = []
    for plugin in plugins_with_themes:
        theme_responses.append(
            ThemeResponse(
                id=plugin.id,
                # Use ID as name for theme identifier in frontend
                # This is the stable identifier (e.g., "cream", "manila")
                name=plugin.id,
                label=plugin.display_name,
                description=plugin.description,
                className=plugin.class_name,
                category=plugin.category,
                version=plugin.version,
                author=plugin.author,
            )
        )
    
    return theme_responses


@router.get("/{theme_id}/stylesheet")
async def get_theme_stylesheet(theme_id: str, request: Request):
    """Get the CSS stylesheet for a specific theme.
    
    This endpoint is public to allow theme stylesheets to be loaded
    before authentication.
    
    Args:
        theme_id: The theme identifier (e.g., "cream", "manila")
        request: FastAPI request object
        
    Returns:
        CSS stylesheet content with text/css content type
        
    Raises:
        HTTPException: If theme not found or stylesheet doesn't exist
    """
    loader = request.app.state.plugin_loader
    plugin = loader.get_plugin(theme_id)
    
    if not plugin or not plugin.has_theme():
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    
    # Get stylesheet path from plugin
    stylesheet_path = plugin.get_stylesheet_path(plugin.stylesheet)
    
    if not stylesheet_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Stylesheet not found for theme '{theme_id}'"
        )
    
    # Read and return CSS content
    try:
        css_content = stylesheet_path.read_text(encoding="utf-8")
        return Response(content=css_content, media_type="text/css")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading stylesheet: {str(e)}"
        )
