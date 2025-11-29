"""FastAPI application for Lab Notebook."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from codex.api.routes.artifacts import router as artifacts_router
from codex.api.routes.entries import router as entries_router
from codex.api.routes.integration_variables import router as integration_variables_router
from codex.api.routes.notebooks import router as notebooks_router
from codex.api.routes.pages import router as pages_router
from codex.api.routes.search import router as search_router
from codex.api.routes.sql import router as sql_router
from codex.api.routes.workspace import router as workspace_router
from codex.api.utils import DEFAULT_WORKSPACE_PATH
from codex.core.workspace import Workspace

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
app.include_router(entries_router, prefix="/api/entries", tags=["entries"])
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(search_router, prefix="/api/search", tags=["search"])
app.include_router(sql_router, prefix="/api/sql", tags=["sql"])
app.include_router(
    integration_variables_router,
    prefix="/api/integration-variables",
    tags=["integration-variables"],
)


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
