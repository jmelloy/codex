"""Main FastAPI application."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import select
from ulid import ULID

from codex.api.routes import (
    agents,
    blocks,
    calendar,
    integrations,
    notebooks,
    oauth,
    plugins,
    projects,
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

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and plugins on startup."""

    await init_system_db()

    # Start WebSocket broadcast loop
    await connection_manager.start_broadcast_loop()

    # Initialize ARQ Redis connection pool for enqueueing background jobs
    try:
        from arq.connections import create_pool

        from codex.worker.settings import get_redis_settings

        app.state.arq_pool = await create_pool(get_redis_settings())
        logger.info("ARQ Redis pool initialized")
    except Exception as e:
        logger.warning(f"Could not connect to Redis for task queue: {e}")
        app.state.arq_pool = None

    # Plugins directory for serving theme/block assets
    default_plugins_dir = Path(__file__).parent.parent.parent / "backend" / "plugins"
    plugins_dir = Path(os.getenv("CODEX_PLUGINS_DIR", default_plugins_dir))
    app.state.plugins_dir = plugins_dir

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

    # Close ARQ Redis pool
    if getattr(app.state, "arq_pool", None) is not None:
        await app.state.arq_pool.close()

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error on %s %s: %s (body type: %s, content-type: %s)",
        request.method,
        request.url.path,
        exc.errors(),
        type(exc.body).__name__ if exc.body is not None else "None",
        request.headers.get("content-type", "missing"),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(ULID())[0:10])
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
app.include_router(
    search.vectorize_router,
    prefix="/api/v1",
    tags=["search"],
)
app.include_router(
    tasks.router,
    prefix="/api/v1/workspaces/{workspace_identifier}/tasks",
    tags=["tasks"],
)
app.include_router(integrations.router, prefix="/api/v1/plugins/integrations", tags=["integrations"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(ws.router, prefix="/api/v1/ws", tags=["websocket"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(agents.session_router, prefix="/api/v1/sessions", tags=["agent-sessions"])
app.include_router(tokens.router, prefix="/api/v1/tokens", tags=["tokens"])
app.include_router(snippets.router, prefix="/api/v1/snippets", tags=["snippets"])
app.include_router(oauth.router, prefix="/api/v1/oauth", tags=["oauth"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["calendar"])
app.include_router(
    projects.nested_router,
    prefix="/api/v1/workspaces/{workspace_identifier}/projects",
    tags=["projects"],
)

# Serve frontend static files if the build is present (production)
_static_dir = Path(__file__).parent.parent / "static"
if not _static_dir.exists():
    _static_dir = Path("/app/static")

if _static_dir.exists() and (_static_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't serve SPA for API paths — let them 404 naturally
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
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
