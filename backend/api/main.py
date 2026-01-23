"""Main FastAPI application."""

import asyncio
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import select

from backend.db.database import init_system_db, DATA_DIRECTORY, get_notebook_session
from backend.db.models import Notebook
from backend.api.routes import workspaces, notebooks, files, search, tasks, markdown, query, users
from core.watcher import NotebookWatcher

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
    workspace_dir = Path(DATA_DIRECTORY) / "workspaces"
    print(f"[watcher] Looking for notebooks in: {workspace_dir}", flush=True)
    os.makedirs(workspace_dir, exist_ok=True)

    if not workspace_dir.exists():
        print("[watcher] Workspace directory does not exist", flush=True)
        return

    user_dirs = list(workspace_dir.iterdir())
    print(f"[watcher] Found {len(user_dirs)} user directories", flush=True)

    for user in user_dirs:
        if not user.is_dir():
            continue
        print(f"[watcher] Checking user directory: {user.name}", flush=True)
        notebook_dirs = list(user.iterdir())
        for notebook in notebook_dirs:
            if not notebook.is_dir():
                continue
            codex_db_path = notebook / ".codex" / "notebook.db"
            print(f"[watcher] Checking notebook at {notebook}", flush=True)
            if not codex_db_path.exists():
                print("[watcher] No .codex/notebook.db found, skipping", flush=True)
                continue

            try:
                nb_session = get_notebook_session(str(notebook))
                nb_result = nb_session.execute(select(Notebook))
                nb_instance = nb_result.scalar_one_or_none()
                nb_session.close()

                if nb_instance is None:
                    print(f"[watcher] No notebook record found in {notebook}", flush=True)
                    continue

                print(f"[watcher] Starting watcher for: {nb_instance.name} (id={nb_instance.id})", flush=True)
                watcher = NotebookWatcher(str(notebook), nb_instance.id)
                watcher.start()
                _active_watchers.append(watcher)
                print(f"[watcher] Watcher started successfully for {nb_instance.name}", flush=True)
            except Exception as e:
                print(f"[watcher] Error starting watcher for {notebook}: {e}", flush=True)
                import traceback
                traceback.print_exc()

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
