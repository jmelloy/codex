"""API routes for theme management."""

from fastapi import APIRouter, Request

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
