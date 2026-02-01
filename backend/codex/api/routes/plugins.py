"""API routes for plugin management."""

from fastapi import APIRouter, HTTPException, Request

from codex.api.schemas import (
    CodexVersionResponse,
    DependencyResponse,
    DependencyTreeResponse,
    PluginDependencyResponse,
    PluginLoadResultResponse,
    PluginResponse,
)
from codex.plugins import get_codex_version

router = APIRouter()


@router.get("/", response_model=list[PluginResponse])
async def list_plugins(request: Request):
    """List all loaded plugins with their metadata.

    Returns information about all plugins including version, dependencies,
    and compatibility status.

    Returns:
        List of all loaded plugins.
    """
    loader = request.app.state.plugin_loader
    plugins = loader.plugins

    responses = []
    for plugin in plugins.values():
        deps = [
            DependencyResponse(
                plugin_id=dep.plugin_id,
                version_constraint=str(dep.constraint),
                optional=dep.optional,
            )
            for dep in plugin.dependencies
        ]

        responses.append(
            PluginResponse(
                id=plugin.id,
                name=plugin.name,
                version=plugin.version,
                type=plugin.type,
                description=plugin.description,
                author=plugin.author,
                license=plugin.license,
                repository=plugin.repository,
                codex_version=plugin.codex_version,
                api_version=plugin.api_version,
                has_dependencies=plugin.has_dependencies,
                dependency_ids=plugin.dependency_ids,
                dependencies=deps,
            )
        )

    return responses


@router.get("/load-result", response_model=PluginLoadResultResponse | None)
async def get_load_result(request: Request):
    """Get the result of the last plugin load operation.

    Returns information about which plugins were loaded successfully,
    which failed, and the load order.

    Returns:
        Plugin load result or None if load_all_plugins hasn't been called.
    """
    loader = request.app.state.plugin_loader
    result = loader.get_load_result()

    if result is None:
        return None

    return PluginLoadResultResponse(**result.to_dict())


@router.get("/load-order", response_model=list[str])
async def get_load_order(request: Request):
    """Get the order in which plugins should be loaded.

    Returns plugins sorted by their dependencies, ensuring dependencies
    are loaded before dependents.

    Returns:
        List of plugin IDs in load order.

    Raises:
        HTTPException: If circular dependencies exist.
    """
    loader = request.app.state.plugin_loader

    try:
        return loader.get_load_order()
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/codex-version", response_model=CodexVersionResponse)
async def get_codex_version_info():
    """Get the current Codex version.

    Returns the version that plugins are checked against for compatibility.

    Returns:
        Codex version information.
    """
    version = get_codex_version()
    return CodexVersionResponse(
        version=str(version),
        major=version.major,
        minor=version.minor,
        patch=version.patch,
    )


@router.get("/circular-dependencies", response_model=list[list[str]])
async def check_circular_dependencies(request: Request):
    """Check for circular dependencies among plugins.

    Returns:
        List of cycles (each cycle is a list of plugin IDs).
    """
    loader = request.app.state.plugin_loader
    return loader.check_circular_dependencies()


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str, request: Request):
    """Get detailed information about a specific plugin.

    Args:
        plugin_id: Plugin identifier.

    Returns:
        Plugin information including dependencies.

    Raises:
        HTTPException: If plugin not found.
    """
    loader = request.app.state.plugin_loader
    plugin = loader.get_plugin(plugin_id)

    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    deps = [
        DependencyResponse(
            plugin_id=dep.plugin_id,
            version_constraint=str(dep.constraint),
            optional=dep.optional,
        )
        for dep in plugin.dependencies
    ]

    return PluginResponse(
        id=plugin.id,
        name=plugin.name,
        version=plugin.version,
        type=plugin.type,
        description=plugin.description,
        author=plugin.author,
        license=plugin.license,
        repository=plugin.repository,
        codex_version=plugin.codex_version,
        api_version=plugin.api_version,
        has_dependencies=plugin.has_dependencies,
        dependency_ids=plugin.dependency_ids,
        dependencies=deps,
    )


@router.get("/{plugin_id}/dependencies", response_model=PluginDependencyResponse)
async def get_plugin_dependencies(plugin_id: str, request: Request):
    """Get detailed dependency information for a plugin.

    Shows all dependencies, their satisfaction status, and which
    plugins depend on this one.

    Args:
        plugin_id: Plugin identifier.

    Returns:
        Complete dependency information.

    Raises:
        HTTPException: If plugin not found.
    """
    loader = request.app.state.plugin_loader
    info = loader.get_plugin_dependencies(plugin_id)

    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    return PluginDependencyResponse(**info.to_dict())


@router.get("/{plugin_id}/dependency-tree", response_model=DependencyTreeResponse)
async def get_dependency_tree(plugin_id: str, request: Request, max_depth: int = 10):
    """Get the full dependency tree for a plugin.

    Returns a nested structure showing all transitive dependencies.

    Args:
        plugin_id: Plugin identifier.
        max_depth: Maximum depth to traverse (default: 10).

    Returns:
        Nested dependency tree.

    Raises:
        HTTPException: If plugin not found.
    """
    loader = request.app.state.plugin_loader
    tree = loader.get_dependency_tree(plugin_id)

    if tree is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    return DependencyTreeResponse(**tree)


@router.get("/{plugin_id}/can-disable")
async def check_can_disable(plugin_id: str, request: Request):
    """Check if a plugin can be disabled without breaking dependencies.

    Args:
        plugin_id: Plugin identifier.

    Returns:
        Object with can_disable status and list of dependent plugins.

    Raises:
        HTTPException: If plugin not found.
    """
    loader = request.app.state.plugin_loader

    if plugin_id not in loader.plugins:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    can_disable, dependents = loader.can_disable_plugin(plugin_id)

    return {
        "can_disable": can_disable,
        "dependent_plugins": dependents,
        "message": (
            "Plugin can be safely disabled"
            if can_disable
            else f"Plugin is required by: {', '.join(dependents)}"
        ),
    }
