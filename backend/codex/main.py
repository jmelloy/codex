"""Main FastAPI application."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import select
from ulid import ULID

from codex.api.routes import (
    agents,
    blocks,
    calendar,
    files,
    folders,
    integrations,
    notebooks,
    oauth,
    plugins,
    query,
    search,
    snippets,
    tasks,
    tokens,
    users,
    workspaces,
    ws,
)
from codex.core.watcher import NotebookWatcher, register_watcher, stop_all_watchers
from codex.core.websocket import connection_manager
from codex.db.database import get_system_session_sync, init_notebook_db, init_system_db
from codex.db.models import Notebook, Workspace
from codex.plugins.loader import PluginLoader
from codex.plugins.service_client import PluginServiceClient

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger(__name__)


async def _register_loaded_plugins_in_db(loader: PluginLoader) -> None:
    """Register all loaded plugins from the PluginLoader into the system database.

    This ensures the database has entries for filesystem-discovered plugins,
    so the PluginRegistry can serve template/view/theme data even when
    the filesystem loader isn't directly accessible (e.g., in route handlers).
    """
    from datetime import datetime, timezone
    from codex.db.database import async_session_maker
    from codex.db.models import Plugin as PluginModel

    if not loader.plugins:
        return

    try:
        async with async_session_maker() as session:
            now = datetime.now(timezone.utc)
            for plugin in loader.plugins.values():
                stmt = select(PluginModel).where(PluginModel.plugin_id == plugin.id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.name = plugin.name
                    existing.version = plugin.version
                    existing.type = plugin.type
                    existing.manifest = plugin.manifest
                    existing.updated_at = now
                    session.add(existing)
                else:
                    db_plugin = PluginModel(
                        plugin_id=plugin.id,
                        name=plugin.name,
                        version=plugin.version,
                        type=plugin.type,
                        enabled=True,
                        manifest=plugin.manifest,
                        installed_at=now,
                        updated_at=now,
                    )
                    session.add(db_plugin)
            await session.commit()
            logger.info(f"Registered {len(loader.plugins)} plugins in database")
    except Exception as e:
        logger.warning(f"Failed to register plugins in database: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and plugins on startup."""

    await init_system_db()

    # Start WebSocket broadcast loop
    await connection_manager.start_broadcast_loop()

    # Default plugins directory is under plugin-service/ at the repository root
    # or use CODEX_PLUGINS_DIR environment variable to override
    default_plugins_dir = Path(__file__).parent.parent.parent / "plugin-service" / "plugins"
    plugins_dir = Path(os.getenv("CODEX_PLUGINS_DIR", default_plugins_dir))
    logger.info(f"Loading plugins from directory: {plugins_dir}")
    loader = PluginLoader(plugins_dir)
    loader.load_all_plugins()
    logger.info(f"Loaded {len(loader.plugins)} plugins")

    # Store plugin loader and directory in app state for use by API routes
    app.state.plugin_loader = loader
    app.state.plugins_dir = plugins_dir

    # Register filesystem-loaded plugins in the database
    await _register_loaded_plugins_in_db(loader)

    # Initialize plugin service client (if configured)
    plugin_service_url = os.getenv("PLUGIN_SERVICE_URL")
    if plugin_service_url:
        try:
            client = PluginServiceClient(
                service_url=plugin_service_url,
                plugins_dir=plugins_dir,
            )
            app.state.plugin_service_client = client
            logger.info(f"Plugin service client configured: {plugin_service_url}")

            # Optionally auto-sync on startup
            if os.getenv("PLUGIN_AUTO_SYNC", "false").lower() == "true":
                logger.info("Auto-syncing plugins from service...")
                result = await client.sync_plugins()
                logger.info(
                    f"Plugin sync: {len(result['installed'])} installed, "
                    f"{len(result['updated'])} updated, "
                    f"{len(result['skipped'])} up-to-date, "
                    f"{len(result['failed'])} failed"
                )
                # Reload plugins after sync
                if result["installed"] or result["updated"]:
                    loader.load_all_plugins()

                # Register all synced plugins in the database
                await _register_loaded_plugins_in_db(loader)
        except Exception as e:
            logger.error(f"Error configuring plugin service client: {e}", exc_info=True)

    # Enable S3 versioning if S3 storage is configured
    try:
        from codex.core.s3_storage import ensure_versioning, is_s3_configured

        if is_s3_configured():
            await asyncio.to_thread(ensure_versioning)
    except Exception as e:
        logger.warning(f"Could not enable S3 versioning: {e}")

    try:
        # Run blocking file I/O in thread pool
        await asyncio.to_thread(_start_notebook_watchers_sync)
    except Exception as e:
        logger.error(f"Error starting notebook watcher: {e}", exc_info=True)

    yield

    # Stop all watchers on shutdown
    stop_all_watchers()

    # Stop WebSocket broadcast loop
    await connection_manager.stop_broadcast_loop()


def _start_notebook_watchers_sync():
    """Start notebook watchers synchronously (runs in thread pool)."""
    logger.info("Starting notebook watchers...")

    # Query notebooks from the system database
    session = get_system_session_sync()
    try:
        # Select notebooks with their workspace relationship to get full paths
        result = session.exec(select(Notebook, Workspace).join(Workspace, Notebook.workspace_id == Workspace.id))
        rows = result.all()
        logger.info(f"Found {len(rows)} notebooks in database")

        for nb, workspace in rows:
            try:
                # Compute full notebook path
                notebook_path = (Path(workspace.path) / nb.path).resolve()  # Convert to absolute path
                codex_db_path = notebook_path / ".codex" / "notebook.db"

                logger.debug(f"Checking notebook: {nb.name} at {notebook_path}")

                if not notebook_path.exists():
                    logger.warning(f"Notebook directory does not exist: {notebook_path}")
                    continue

                if not codex_db_path.exists():
                    logger.debug(f"No .codex/notebook.db found at {codex_db_path}, skipping")
                    continue

                # Ensure notebook database schema is up to date before starting watcher
                try:
                    init_notebook_db(str(notebook_path))
                except Exception as e:
                    logger.error(f"Failed to initialize notebook database for {nb.name}: {e}")
                    continue

                logger.info(f"Starting watcher for: {nb.name} (id={nb.id})")
                watcher = NotebookWatcher(str(notebook_path), nb.id)
                watcher.start()
                register_watcher(watcher)
                logger.info(f"Watcher started successfully for {nb.name}")

            except Exception as e:
                logger.error(f"Error starting watcher for notebook {nb.name}: {e}", exc_info=True)
    finally:
        session.close()

    from codex.core.watcher import get_active_watchers

    logger.info(f"Finished starting {len(get_active_watchers())} watchers")


app = FastAPI(
    title="Codex API",
    description="A hierarchical digital laboratory journal system",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(ULID()))
    request_id_var.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "healthy", "version": os.environ.get("BUILD_VERSION", "dev")}


# Include routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(notebooks.router, prefix="/api/v1/notebooks", tags=["notebooks"])
app.include_router(
    notebooks.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/notebooks",
    tags=["notebooks"],
)
app.include_router(
    files.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/notebooks/{notebook_identifier}/files",
    tags=["files"],
)
app.include_router(
    folders.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/notebooks/{notebook_identifier}/folders",
    tags=["folders"],
)
app.include_router(
    blocks.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/notebooks/{notebook_identifier}/blocks",
    tags=["blocks"],
)
app.include_router(
    search.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/search",
    tags=["search"],
)
app.include_router(
    search.notebook_nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/notebooks/{notebook_identifier}/search",
    tags=["search"],
)
app.include_router(
    integrations.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/notebooks/{notebook_identifier}/integrations",
    tags=["integrations"],
)
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
app.include_router(integrations.router, prefix="/api/v1/plugins/integrations", tags=["integrations"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(ws.router, prefix="/api/v1/ws", tags=["websocket"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(agents.session_router, prefix="/api/v1/sessions", tags=["agent-sessions"])
app.include_router(tokens.router, prefix="/api/v1/tokens", tags=["tokens"])
app.include_router(snippets.router, prefix="/api/v1/snippets", tags=["snippets"])
app.include_router(oauth.router, prefix="/api/v1/oauth", tags=["oauth"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["calendar"])

# Serve frontend static files if the build is present (production)
_static_dir = Path(__file__).parent.parent / "static"
if not _static_dir.exists():
    _static_dir = Path("/app/static")

if _static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file = _static_dir / full_path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(_static_dir / "index.html")


if __name__ == "__main__":
    import uvicorn

    from codex.core.logging import get_logging_config

    debug = os.getenv("DEBUG", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "colored" if debug else "plain").lower()
    log_sql = os.getenv("LOG_SQL", "false").lower() == "true"

    logging_config = get_logging_config(log_level, log_format, log_sql)

    uvicorn.run(
        "codex.main:app",
        host="0.0.0.0",
        port=8000,
        reload=debug,
        log_config=logging_config,
        log_level=log_level.lower(),
    )
