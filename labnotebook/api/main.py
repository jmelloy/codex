"""FastAPI application for Lab Notebook."""


from fastapi import FastAPI

from labnotebook.api.routes.artifacts import router as artifacts_router
from labnotebook.api.routes.entries import router as entries_router
from labnotebook.api.routes.notebooks import router as notebooks_router
from labnotebook.api.routes.pages import router as pages_router
from labnotebook.api.routes.search import router as search_router
from labnotebook.api.routes.workspace import router as workspace_router

app = FastAPI(
    title="Lab Notebook API",
    description="A hierarchical digital laboratory journal system",
    version="0.1.0",
)

# Include routers
app.include_router(workspace_router, prefix="/api", tags=["workspace"])
app.include_router(notebooks_router, prefix="/api/notebooks", tags=["notebooks"])
app.include_router(pages_router, prefix="/api/pages", tags=["pages"])
app.include_router(entries_router, prefix="/api/entries", tags=["entries"])
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])
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
