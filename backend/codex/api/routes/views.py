"""API routes for view management."""

from fastapi import APIRouter, Request

from codex.api.schemas import ViewResponse

router = APIRouter()


@router.get("/", response_model=list[ViewResponse])
async def get_available_views(request: Request):
    """Get all available view types from the plugin system.
    
    This endpoint is public (no authentication required) to allow
    view discovery before rendering. View metadata does not contain
    sensitive information.
    
    Returns all plugins that provide views, regardless of plugin type.
    This allows any plugin (view, theme, integration) to expose views.
    
    Returns:
        List of available views from all plugins with their metadata.
    """
    loader = request.app.state.plugin_loader
    # Use capability-based filtering instead of type-based
    plugins_with_views = loader.get_plugins_with_views()
    
    # Collect all views from all plugins
    view_responses = []
    for plugin in plugins_with_views:
        for view in plugin.views:
            view_responses.append(
                ViewResponse(
                    id=view["id"],
                    name=view["name"],
                    description=view.get("description", ""),
                    icon=view.get("icon", "📄"),
                    plugin_id=plugin.id,
                    plugin_name=plugin.name,
                    config_schema=view.get("config_schema", {}),
                )
            )
    
    return view_responses
