"""Service for indexing markdown files and their frontmatter metadata."""

import hashlib
import json
import logging
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Optional

from core.markdown import parse_markdown_file
from db.models import MarkdownFile
from sqlalchemy.orm import Session

# Set up logging
logger = logging.getLogger(__name__)


def _now() -> datetime:
    """Get current time without timezone info for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hex string of file hash
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def index_markdown_file(
    session: Session,
    file_path: Path,
    base_path: Path,
) -> Optional[MarkdownFile]:
    """Index a single markdown file and extract its frontmatter.
    
    Args:
        session: Database session
        file_path: Absolute path to the markdown file
        base_path: Base path to compute relative path from
        
    Returns:
        MarkdownFile instance or None if indexing failed
    """
    if not file_path.exists() or not file_path.is_file():
        return None
    
    # Only index markdown files
    if file_path.suffix.lower() not in [".md", ".markdown"]:
        return None
    
    try:
        # Compute relative path
        relative_path = str(file_path.relative_to(base_path))
        
        # Get file stats
        stat_info = file_path.stat()
        file_size = stat_info.st_size
        file_modified = datetime.fromtimestamp(
            stat_info.st_mtime, tz=timezone.utc
        ).replace(tzinfo=None)
        
        # Compute file hash
        file_hash = compute_file_hash(file_path)
        
        # Check if file is already indexed with same hash
        existing = (
            session.query(MarkdownFile)
            .filter(MarkdownFile.relative_path == relative_path)
            .first()
        )
        
        if existing and existing.file_hash == file_hash:
            # File hasn't changed, no need to re-index
            return existing
        
        # Parse markdown to extract frontmatter
        doc = parse_markdown_file(str(file_path))
        title = doc.frontmatter.get("title", file_path.stem)
        
        # Convert frontmatter to JSON, handling datetime and date objects
        def serialize_frontmatter(obj):
            """Convert datetime, date, and other non-serializable objects to strings."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        frontmatter_json = json.dumps(
            doc.frontmatter,
            default=serialize_frontmatter
        ) if doc.frontmatter else json.dumps({})
        
        now = _now()
        
        if existing:
            # Update existing record
            existing.path = str(file_path)
            existing.title = title
            existing.file_hash = file_hash
            existing.frontmatter = frontmatter_json
            existing.file_size = file_size
            existing.file_modified = file_modified
            existing.indexed_at = now
            existing.updated_at = now
            session.commit()
            return existing
        else:
            # Create new record
            markdown_file = MarkdownFile(
                path=str(file_path),
                relative_path=relative_path,
                title=title,
                file_hash=file_hash,
                frontmatter=frontmatter_json,
                file_size=file_size,
                file_modified=file_modified,
                indexed_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(markdown_file)
            session.commit()
            return markdown_file
            
    except Exception as e:
        logger.error(f"Failed to index {file_path}: {e}", exc_info=True)
        return None


def index_directory(
    session: Session,
    directory: Path,
    base_path: Optional[Path] = None,
    recursive: bool = True,
) -> int:
    """Index all markdown files in a directory.
    
    Args:
        session: Database session
        directory: Directory to scan
        base_path: Base path for computing relative paths (defaults to directory)
        recursive: Whether to scan subdirectories
        
    Returns:
        Number of files indexed
    """
    if not directory.exists() or not directory.is_dir():
        return 0
    
    if base_path is None:
        base_path = directory
    
    indexed_count = 0
    
    try:
        for item in directory.iterdir():
            # Skip hidden files and directories
            if item.name.startswith("."):
                continue
            
            if item.is_dir() and recursive:
                indexed_count += index_directory(session, item, base_path, recursive)
            elif item.is_file():
                result = index_markdown_file(session, item, base_path)
                if result:
                    indexed_count += 1
    except PermissionError as e:
        # Log permission errors but continue scanning other files
        logger.warning(f"Permission denied accessing {directory}: {e}")
    
    return indexed_count


def search_markdown_files(
    session: Session,
    query: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Search indexed markdown files.
    
    Args:
        session: Database session
        query: Search query (searches in title and frontmatter)
        limit: Maximum number of results
        
    Returns:
        List of markdown file dictionaries
    """
    query_obj = session.query(MarkdownFile)
    
    if query:
        # Search in title and frontmatter JSON
        search_term = f"%{query}%"
        query_obj = query_obj.filter(
            (MarkdownFile.title.ilike(search_term)) |
            (MarkdownFile.frontmatter.ilike(search_term))
        )
    
    results = query_obj.order_by(MarkdownFile.indexed_at.desc()).limit(limit).all()
    
    return [
        {
            "id": mf.id,
            "path": mf.path,
            "relative_path": mf.relative_path,
            "title": mf.title,
            "file_hash": mf.file_hash,
            "frontmatter": json.loads(mf.frontmatter) if mf.frontmatter else {},
            "file_size": mf.file_size,
            "file_modified": mf.file_modified.isoformat() if mf.file_modified else None,
            "indexed_at": mf.indexed_at.isoformat() if mf.indexed_at else None,
        }
        for mf in results
    ]


def remove_stale_entries(session: Session, base_path: Path) -> int:
    """Remove index entries for files that no longer exist.
    
    Args:
        session: Database session
        base_path: Base path to check files against
        
    Returns:
        Number of stale entries removed
    """
    all_files = session.query(MarkdownFile).all()
    removed_count = 0
    
    for markdown_file in all_files:
        file_path = Path(markdown_file.path)
        if not file_path.exists():
            session.delete(markdown_file)
            removed_count += 1
    
    if removed_count > 0:
        session.commit()
    
    return removed_count
