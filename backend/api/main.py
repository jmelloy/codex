"""Main FastAPI application."""

import asyncio
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import select

from backend.db.database import init_system_db, DATA_DIRECTORY, get_notebook_session, get_system_session_sync
from backend.db.models import Notebook, Workspace
from backend.api.routes import workspaces, notebooks, files, search, tasks, markdown, query, users
from backend.core.watcher import NotebookWatcher

# Global registry of active watchers
_active_watchers: list[NotebookWatcher] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    
    await init_system_db()
    

    try:
        # Run blocking file I/O in thread pool
        await asyncio.to_thread(_start_notebook_watchers_sync)
    except Exception as e:
        print(f"[lifespan] Error starting notebook watcher: {e}", flush=True)
        import traceback
        traceback.print_exc()

    
    yield
    

    # Stop all watchers on shutdown
    for watcher in _active_watchers:
        try:
            watcher.stop()
        except Exception as e:
            print(f"[lifespan] Error stopping watcher: {e}", flush=True)


def _start_notebook_watchers_sync():
    """Start notebook watchers synchronously (runs in thread pool)."""
    print("[watcher] Starting notebook watchers...", flush=True)

    # Query notebooks from the system database
    session = get_system_session_sync()
    try:
        # Select notebooks with their workspace relationship to get full paths
        result = session.execute(select(Notebook))
        notebooks = result.scalars().all()
        print(f"[watcher] Found {len(notebooks)} notebooks in database", flush=True)

        for nb in notebooks:
            try:
                # Get the workspace to compute full notebook path
                workspace_result = session.execute(
                    select(Workspace).where(Workspace.id == nb.workspace_id)
                )
                workspace = workspace_result.scalar_one_or_none()

                if workspace is None:
                    print(f"[watcher] Workspace not found for notebook {nb.name} (id={nb.id})", flush=True)
                    continue

                # Compute full notebook path
                notebook_path = Path(workspace.path) / nb.path
                codex_db_path = notebook_path / ".codex" / "notebook.db"

                print(f"[watcher] Checking notebook: {nb.name} at {notebook_path}", flush=True)

                if not notebook_path.exists():
                    print(f"[watcher] Notebook directory does not exist: {notebook_path}", flush=True)
                    continue

                if not codex_db_path.exists():
                    print(f"[watcher] No .codex/notebook.db found at {codex_db_path}, skipping", flush=True)
                    continue

                print(f"[watcher] Starting watcher for: {nb.name} (id={nb.id})", flush=True)
                watcher = NotebookWatcher(str(notebook_path), nb.id)
                watcher.start()
                _active_watchers.append(watcher)
                print(f"[watcher] Watcher started successfully for {nb.name}", flush=True)

            except Exception as e:
                print(f"[watcher] Error starting watcher for notebook {nb.name}: {e}", flush=True)
                import traceback
                traceback.print_exc()
    finally:
        session.close()

    print(f"[watcher] Finished starting {len(_active_watchers)} watchers", flush=True)
        

app = FastAPI(
    title="Codex API",
    description="A hierarchical digital laboratory journal system",
    version="0.1.0",
    lifespan=lifespan,
)

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


# Include routers
app.include_router(users.router, tags=["users"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(notebooks.router, prefix="/api/v1/notebooks", tags=["notebooks"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(markdown.router, prefix="/api/v1/markdown", tags=["markdown"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])


if __name__ == "__main__":
    import uvicorn

    debug = os.getenv("DEBUG", "false").lower() == "true"
    log_level = "debug" if debug else "info"

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=log_level, reload=debug)
