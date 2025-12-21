"""FastAPI application for Lab Notebook."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from api.routes.notebooks import router as notebooks_router
from api.routes.pages import router as pages_router
from api.routes.search import router as search_router
from api.routes.workspace import router as workspace_router
from api.utils import DEFAULT_WORKSPACE_PATH
from core.workspace import Workspace

DEBUG = os.environ.get("DEBUG", "false") == "true"
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize workspace on startup if needed."""
    workspace_path = Path(DEFAULT_WORKSPACE_PATH)
    try:
        Workspace.load(workspace_path)
    except ValueError:
        Workspace.initialize(workspace_path, "Default Workspace")
    yield


app = FastAPI(
    title="Codex API",
    description="A hierarchical digital laboratory journal system",
    version="0.1.0",
    lifespan=lifespan,
    debug=DEBUG,
)

# Include routers
app.include_router(workspace_router, prefix="/api", tags=["workspace"])
app.include_router(notebooks_router, prefix="/api/notebooks", tags=["notebooks"])
app.include_router(pages_router, prefix="/api/pages", tags=["pages"])
app.include_router(search_router, prefix="/api/search", tags=["search"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Lab Notebook API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
