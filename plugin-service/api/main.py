"""Plugin Service - FastAPI application.

Serves a plugin catalog with SHA-256 integrity checksums and downloadable
plugin archives. The main Codex backend uses this service to discover,
download, and verify plugins.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from .catalog import PluginCatalog

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the plugin catalog on startup."""
    plugins_dir = Path(os.getenv("PLUGIN_SERVICE_DIR", "/app/plugins"))
    logger.info(f"Building plugin catalog from: {plugins_dir}")

    catalog = PluginCatalog(plugins_dir=plugins_dir)
    catalog.build()
    app.state.catalog = catalog

    yield


app = FastAPI(
    title="Codex Plugin Service",
    description="Plugin catalog and distribution service for Codex",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "plugin-service"}


@app.get("/api/v1/catalog")
async def list_catalog(
    plugin_type: str | None = Query(None, description="Filter by plugin type"),
):
    """List all available plugins in the catalog.

    Returns manifests and SHA-256 checksums for each plugin so the
    consumer can verify integrity after download.
    """
    catalog: PluginCatalog = app.state.catalog
    entries = catalog.list_entries(plugin_type=plugin_type)
    return {
        "plugins": [e.to_dict() for e in entries],
        "total": len(entries),
    }


@app.get("/api/v1/catalog/{plugin_id}")
async def get_plugin_info(plugin_id: str):
    """Get detailed info for a specific plugin."""
    catalog: PluginCatalog = app.state.catalog
    entry = catalog.get_entry(plugin_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")
    return entry.to_dict()


@app.get("/api/v1/catalog/{plugin_id}/download")
async def download_plugin(plugin_id: str):
    """Download a plugin archive (tar.gz).

    The response includes the SHA-256 checksum in the X-Checksum-SHA256 header
    so the downloader can verify integrity.
    """
    catalog: PluginCatalog = app.state.catalog
    entry = catalog.get_entry(plugin_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    archive = catalog.get_archive(plugin_id)
    if not archive:
        raise HTTPException(status_code=500, detail="Archive not available")

    return Response(
        content=archive,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{plugin_id}-{entry.version}.tar.gz"',
            "X-Checksum-SHA256": entry.archive_sha256,
            "X-Plugin-Version": entry.version,
        },
    )


@app.post("/api/v1/catalog/refresh")
async def refresh_catalog():
    """Rebuild the catalog by re-scanning the plugins directory.

    Useful after adding/updating plugins on disk.
    """
    catalog: PluginCatalog = app.state.catalog
    catalog.build()
    return {
        "message": "Catalog refreshed",
        "total": len(catalog.entries),
    }


if __name__ == "__main__":
    import uvicorn

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=log_level)

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8090,
        log_level=log_level.lower(),
    )
