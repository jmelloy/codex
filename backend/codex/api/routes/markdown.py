"""Markdown parsing and viewing API routes."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from codex.api.utils import get_workspace_path
from codex.core.markdown import parse_markdown_file, MarkdownDocument
from codex.core.markdown_renderers import get_registry
from codex.core.workspace import Workspace

router = APIRouter()


class MarkdownBlock(BaseModel):
    """Block in markdown document."""

    type: str
    content: str


class ParsedMarkdownResponse(BaseModel):
    """Response model for parsed markdown."""

    frontmatter: Dict[str, Any]
    blocks: List[MarkdownBlock]
    content: str


@router.get("/markdown/parse", response_model=ParsedMarkdownResponse)
async def parse_markdown(
    path: str = Query(..., description="Relative path to the markdown file"),
    workspace_path: Optional[str] = Query(None),
):
    """Parse a markdown file and return structured data.

    This endpoint parses markdown files following the Codex format:
    - YAML frontmatter enclosed in --- delimiters
    - Content blocks enclosed in ::: delimiters
    - Regular markdown content

    Args:
        path: Relative path to the markdown file
        workspace_path: Optional workspace path

    Returns:
        Parsed markdown with frontmatter, blocks, and content
    """
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))

        # Sanitize path to prevent directory traversal
        safe_path = Path(path).as_posix()
        if ".." in safe_path or safe_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Support files from both notebooks and artifacts directories
        file_path = None
        for base_dir in [ws.notebooks_path, ws.artifacts_path]:
            potential_path = base_dir / safe_path
            if potential_path.exists() and potential_path.is_file():
                try:
                    potential_path.resolve().relative_to(base_dir.resolve())
                    file_path = potential_path
                    break
                except ValueError:
                    continue

        if file_path is None:
            raise HTTPException(status_code=404, detail="File not found")

        # Check if it's a markdown file
        if not file_path.suffix.lower() in [".md", ".markdown"]:
            raise HTTPException(
                status_code=400, detail="File is not a markdown file"
            )

        # Parse the markdown file
        doc = parse_markdown_file(str(file_path))

        # Convert to response model
        blocks = [MarkdownBlock(type=b["type"], content=b["content"]) for b in doc.blocks]

        return ParsedMarkdownResponse(
            frontmatter=doc.frontmatter,
            blocks=blocks,
            content=doc.content,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/markdown/frontmatter")
async def get_frontmatter(
    path: str = Query(..., description="Relative path to the markdown file"),
    workspace_path: Optional[str] = Query(None),
):
    """Get only the frontmatter from a markdown file.

    Args:
        path: Relative path to the markdown file
        workspace_path: Optional workspace path

    Returns:
        Dictionary of frontmatter data
    """
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))

        # Sanitize path to prevent directory traversal
        safe_path = Path(path).as_posix()
        if ".." in safe_path or safe_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Support files from both notebooks and artifacts directories
        file_path = None
        for base_dir in [ws.notebooks_path, ws.artifacts_path]:
            potential_path = base_dir / safe_path
            if potential_path.exists() and potential_path.is_file():
                try:
                    potential_path.resolve().relative_to(base_dir.resolve())
                    file_path = potential_path
                    break
                except ValueError:
                    continue

        if file_path is None:
            raise HTTPException(status_code=404, detail="File not found")

        # Check if it's a markdown file
        if not file_path.suffix.lower() in [".md", ".markdown"]:
            raise HTTPException(
                status_code=400, detail="File is not a markdown file"
            )

        # Parse the markdown file
        doc = parse_markdown_file(str(file_path))

        return {"frontmatter": doc.frontmatter}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/markdown/frontmatter/rendered")
async def get_rendered_frontmatter(
    path: str = Query(..., description="Relative path to the markdown file"),
    workspace_path: Optional[str] = Query(None),
):
    """Get rendered frontmatter with type information for display.

    This endpoint parses the frontmatter and applies appropriate renderers
    to each field, providing type information and formatted values suitable
    for display in the UI.

    Args:
        path: Relative path to the markdown file
        workspace_path: Optional workspace path

    Returns:
        Dictionary of rendered frontmatter fields with type info
    """
    try:
        ws = Workspace.load(get_workspace_path(workspace_path))

        # Sanitize path to prevent directory traversal
        safe_path = Path(path).as_posix()
        if ".." in safe_path or safe_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Support files from both notebooks and artifacts directories
        file_path = None
        for base_dir in [ws.notebooks_path, ws.artifacts_path]:
            potential_path = base_dir / safe_path
            if potential_path.exists() and potential_path.is_file():
                try:
                    potential_path.resolve().relative_to(base_dir.resolve())
                    file_path = potential_path
                    break
                except ValueError:
                    continue

        if file_path is None:
            raise HTTPException(status_code=404, detail="File not found")

        # Check if it's a markdown file
        if not file_path.suffix.lower() in [".md", ".markdown"]:
            raise HTTPException(
                status_code=400, detail="File is not a markdown file"
            )

        # Parse the markdown file
        doc = parse_markdown_file(str(file_path))

        # Render frontmatter fields
        registry = get_registry()
        rendered = registry.render_frontmatter(doc.frontmatter)

        return {"rendered": rendered}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
