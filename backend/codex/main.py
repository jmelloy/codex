"""Main FastAPI application."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from ulid import ULID

from codex.api.routes import files, folders, markdown, notebooks, query, search, tasks, themes, users, workspaces
from codex.core.watcher import NotebookWatcher
from codex.db.database import get_system_session_sync, init_notebook_db, init_system_db
from codex.db.models import Notebook, Workspace

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger(__name__)

# Global registry of active watchers
_active_watchers: list[NotebookWatcher] = []


def get_active_watchers() -> list[NotebookWatcher]:
    """Get the list of active notebook watchers."""
    return _active_watchers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""

    await init_system_db()

    try:
        # Run blocking file I/O in thread pool
        await asyncio.to_thread(_start_notebook_watchers_sync)
    except Exception as e:
        logger.error(f"Error starting notebook watcher: {e}", exc_info=True)

    yield

    # Stop all watchers on shutdown
    for watcher in _active_watchers:
        try:
            watcher.stop()
        except Exception as e:
            logger.error(f"Error stopping watcher: {e}", exc_info=True)


def _start_notebook_watchers_sync():
    """Start notebook watchers synchronously (runs in thread pool)."""
    logger.info("Starting notebook watchers...")

    # Query notebooks from the system database
    session = get_system_session_sync()
    try:
        # Select notebooks with their workspace relationship to get full paths
        result = session.exec(select(Notebook, Workspace).join(Workspace, Notebook.workspace_id == Workspace.id))
        notebooks = result.scalars().all()
        logger.info(f"Found {len(notebooks)} notebooks in database")

        for nb in notebooks:
            try:
                workspace = nb.workspace
                if not workspace:
                    logger.warning(f"Notebook {nb.name} (id={nb.id}) has no associated workspace, skipping")
                    continue
                # Compute full notebook path
                notebook_path = Path(workspace.path) / nb.path
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
                _active_watchers.append(watcher)
                logger.info(f"Watcher started successfully for {nb.name}")

            except Exception as e:
                logger.error(f"Error starting watcher for notebook {nb.name}: {e}", exc_info=True)
    finally:
        session.close()

    logger.info(f"Finished starting {len(_active_watchers)} watchers")


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


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Codex API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
async def health():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "healthy", "version": "0.1.0"}


# Include routers
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(notebooks.router, prefix="/api/v1/notebooks", tags=["notebooks"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(folders.router, prefix="/api/v1/folders", tags=["folders"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(markdown.router, prefix="/api/v1/markdown", tags=["markdown"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
app.include_router(themes.router, prefix="/api/v1/themes", tags=["themes"])

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
