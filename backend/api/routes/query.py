"""Query routes for dynamic views."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.api.auth import get_current_active_user
from backend.db.database import get_notebook_session, get_system_session
from backend.db.models import FileMetadata, FileTag, Notebook, Tag, User, Workspace

router = APIRouter()


class ViewQuery(BaseModel):
    """Query model for dynamic views."""

    # Scope
    notebook_ids: list[int] | None = None
    paths: list[str] | None = None

    # Filtering
    tags: list[str] | None = None
    tags_any: list[str] | None = None
    file_types: list[str] | None = None

    # Property filtering
    properties: dict[str, Any] | None = None
    properties_exists: list[str] | None = None

    # Date filtering
    created_after: str | None = None
    created_before: str | None = None
    modified_after: str | None = None
    modified_before: str | None = None

    # Date properties
    date_property: str | None = None
    date_after: str | None = None
    date_before: str | None = None

    # Content filtering
    content_search: str | None = None

    # Sorting & pagination
    sort: str | None = None
    limit: int = 100
    offset: int = 0

    # Aggregation
    group_by: str | None = None


class QueryResult(BaseModel):
    """Result model for queries."""

    files: list[dict[str, Any]]
    groups: dict[str, list[dict[str, Any]]] | None = None
    total: int
    limit: int
    offset: int


def parse_sort_field(sort_str: str) -> tuple[str, bool]:
    """Parse sort string into field and direction.

    Args:
        sort_str: Sort string like "created_at desc" or "title asc"

    Returns:
        Tuple of (field, is_desc)
    """
    parts = sort_str.strip().split()
    field = parts[0]
    is_desc = len(parts) > 1 and parts[1].lower() == "desc"
    return field, is_desc


def apply_property_filter(files: list[FileMetadata], property_filters: dict[str, Any]) -> list[FileMetadata]:
    """Filter files by properties.

    Args:
        files: List of file metadata
        property_filters: Dictionary of property filters

    Returns:
        Filtered list of files
    """
    filtered = []
    for file in files:
        if not file.properties:
            continue

        try:
            properties = json.loads(file.properties)
        except json.JSONDecodeError:
            continue

        matches = True
        for key, value in property_filters.items():
            if key not in properties:
                matches = False
                break

            # Handle list values (OR logic)
            if isinstance(value, list):
                if properties[key] not in value:
                    matches = False
                    break
            else:
                if properties[key] != value:
                    matches = False
                    break

        if matches:
            filtered.append(file)

    return filtered


def apply_property_exists_filter(files: list[FileMetadata], property_keys: list[str]) -> list[FileMetadata]:
    """Filter files that have specific properties defined.

    Args:
        files: List of file metadata
        property_keys: List of property keys that must exist

    Returns:
        Filtered list of files
    """
    filtered = []
    for file in files:
        if not file.properties:
            continue

        try:
            properties = json.loads(file.properties)
        except json.JSONDecodeError:
            continue

        if all(key in properties for key in property_keys):
            filtered.append(file)

    return filtered


def apply_date_property_filter(
    files: list[FileMetadata], date_property: str, date_after: str | None, date_before: str | None
) -> list[FileMetadata]:
    """Filter files by a date property value.

    Args:
        files: List of file metadata
        date_property: Name of the property containing a date
        date_after: ISO date string (inclusive)
        date_before: ISO date string (inclusive)

    Returns:
        Filtered list of files
    """
    filtered = []
    for file in files:
        if not file.properties:
            continue

        try:
            properties = json.loads(file.properties)
        except json.JSONDecodeError:
            continue

        if date_property not in properties:
            continue

        try:
            prop_date = datetime.fromisoformat(properties[date_property].replace("Z", "+00:00"))

            if date_after:
                after_dt = datetime.fromisoformat(date_after.replace("Z", "+00:00"))
                if prop_date < after_dt:
                    continue

            if date_before:
                before_dt = datetime.fromisoformat(date_before.replace("Z", "+00:00"))
                if prop_date > before_dt:
                    continue

            filtered.append(file)
        except (ValueError, AttributeError):
            # Skip files with invalid date values
            continue

    return filtered


def apply_path_filter(files: list[FileMetadata], path_patterns: list[str]) -> list[FileMetadata]:
    """Filter files by path patterns (supports glob-like matching).

    Args:
        files: List of file metadata
        path_patterns: List of path patterns

    Returns:
        Filtered list of files
    """
    from fnmatch import fnmatch

    filtered = []
    for file in files:
        for pattern in path_patterns:
            if fnmatch(file.path, pattern):
                filtered.append(file)
                break

    return filtered


def sort_files(files: list[FileMetadata], sort_str: str) -> list[FileMetadata]:
    """Sort files by field.

    Args:
        files: List of file metadata
        sort_str: Sort string like "created_at desc" or "properties.priority desc"

    Returns:
        Sorted list of files
    """
    field, is_desc = parse_sort_field(sort_str)

    # Handle property sorting
    if field.startswith("properties."):
        prop_key = field.split(".", 1)[1]

        def get_sort_key(file: FileMetadata) -> Any:
            if not file.properties:
                return None
            try:
                properties = json.loads(file.properties)
                return properties.get(prop_key)
            except json.JSONDecodeError:
                return None

        return sorted(files, key=get_sort_key, reverse=is_desc)

    # Handle standard field sorting
    if hasattr(FileMetadata, field):
        return sorted(files, key=lambda f: getattr(f, field) or "", reverse=is_desc)

    return files


def group_files(files: list[FileMetadata], group_by: str) -> dict[str, list[dict[str, Any]]]:
    """Group files by a field or property.

    Args:
        files: List of file metadata
        group_by: Field or property to group by

    Returns:
        Dictionary mapping group keys to file lists
    """
    groups: dict[str, list[dict[str, Any]]] = {}

    for file in files:
        # Determine group key
        if group_by.startswith("properties."):
            prop_key = group_by.split(".", 1)[1]
            if file.properties:
                try:
                    properties = json.loads(file.properties)
                    group_key = str(properties.get(prop_key, "undefined"))
                except json.JSONDecodeError:
                    group_key = "undefined"
            else:
                group_key = "undefined"
        elif hasattr(file, group_by):
            group_key = str(getattr(file, group_by) or "undefined")
        else:
            group_key = "undefined"

        if group_key not in groups:
            groups[group_key] = []

        groups[group_key].append(file_to_dict(file))

    return groups


def file_to_dict(file: FileMetadata) -> dict[str, Any]:
    """Convert FileMetadata to dictionary.

    Args:
        file: File metadata object

    Returns:
        Dictionary representation
    """
    properties = None
    if file.properties:
        try:
            properties = json.loads(file.properties)
        except json.JSONDecodeError:
            pass

    return {
        "id": file.id,
        "notebook_id": file.notebook_id,
        "path": file.path,
        "filename": file.filename,
        "file_type": file.file_type,
        "size": file.size,
        "hash": file.hash,
        "title": file.title,
        "description": file.description,
        "properties": properties,
        "created_at": file.created_at.isoformat() if file.created_at else None,
        "updated_at": file.updated_at.isoformat() if file.updated_at else None,
        "file_modified_at": file.file_modified_at.isoformat() if file.file_modified_at else None,
    }


@router.post("/")
async def query_files(
    workspace_id: int,
    query: ViewQuery,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_system_session),
):
    """Query files across notebooks with filtering, sorting, and grouping.

    Args:
        workspace_id: Workspace ID
        query: Query parameters
        current_user: Current authenticated user
        session: Database session

    Returns:
        Query results with files and optional grouping
    """
    # Verify workspace access
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == current_user.id)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace_path = Path(workspace.path)
    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail="Workspace path not found")

    # Collect all notebooks in workspace
    all_files: list[FileMetadata] = []

    for item in workspace_path.iterdir():
        if not item.is_dir():
            continue

        codex_dir = item / ".codex"
        notebook_db_path = codex_dir / "notebook.db"
        if not notebook_db_path.exists():
            continue

        try:
            nb_session = get_notebook_session(str(item))

            # Get notebook to check if it matches filter
            nb_result = nb_session.execute(select(Notebook))
            notebook = nb_result.scalar_one_or_none()

            if not notebook:
                nb_session.close()
                continue

            # Skip if not in requested notebook_ids
            if query.notebook_ids and notebook.id not in query.notebook_ids:
                nb_session.close()
                continue

            # Build base query
            files_query = select(FileMetadata).where(FileMetadata.notebook_id == notebook.id)

            # Apply file type filter
            if query.file_types:
                files_query = files_query.where(FileMetadata.file_type.in_(query.file_types))

            # Apply date filters
            if query.created_after:
                created_after_dt = datetime.fromisoformat(query.created_after.replace("Z", "+00:00"))
                files_query = files_query.where(FileMetadata.created_at >= created_after_dt)

            if query.created_before:
                created_before_dt = datetime.fromisoformat(query.created_before.replace("Z", "+00:00"))
                files_query = files_query.where(FileMetadata.created_at <= created_before_dt)

            if query.modified_after:
                modified_after_dt = datetime.fromisoformat(query.modified_after.replace("Z", "+00:00"))
                files_query = files_query.where(FileMetadata.file_modified_at >= modified_after_dt)

            if query.modified_before:
                modified_before_dt = datetime.fromisoformat(query.modified_before.replace("Z", "+00:00"))
                files_query = files_query.where(FileMetadata.file_modified_at <= modified_before_dt)

            # Apply tag filters
            if query.tags or query.tags_any:
                files_query = files_query.join(FileTag).join(Tag)

                if query.tags:
                    # ALL tags (AND logic) - need to check this separately
                    files_query = files_query.where(Tag.name.in_(query.tags))
                elif query.tags_any:
                    # ANY tags (OR logic)
                    files_query = files_query.where(Tag.name.in_(query.tags_any))

            files_result = nb_session.execute(files_query)
            files = list(files_result.scalars().all())

            # For AND tag logic, filter to files that have ALL tags
            if query.tags and len(query.tags) > 1:
                filtered_files = []
                for file in files:
                    file_tags_query = (
                        select(Tag).join(FileTag).where(FileTag.file_id == file.id).where(Tag.notebook_id == notebook.id)
                    )
                    file_tags_result = nb_session.execute(file_tags_query)
                    file_tags = {tag.name for tag in file_tags_result.scalars().all()}

                    if all(tag in file_tags for tag in query.tags):
                        filtered_files.append(file)

                files = filtered_files

            all_files.extend(files)
            nb_session.close()

        except Exception as e:
            print(f"Error querying notebook {item}: {e}")
            import traceback

            traceback.print_exc()

    # Apply property filters (post-query since properties are JSON)
    if query.properties:
        all_files = apply_property_filter(all_files, query.properties)

    if query.properties_exists:
        all_files = apply_property_exists_filter(all_files, query.properties_exists)

    # Apply date property filter
    if query.date_property and (query.date_after or query.date_before):
        all_files = apply_date_property_filter(all_files, query.date_property, query.date_after, query.date_before)

    # Apply path filter
    if query.paths:
        all_files = apply_path_filter(all_files, query.paths)

    # Apply content search (simplified - just searches in title/description for now)
    if query.content_search:
        search_term = query.content_search.lower()
        all_files = [
            f
            for f in all_files
            if (f.title and search_term in f.title.lower())
            or (f.description and search_term in f.description.lower())
        ]

    # Sort files
    if query.sort:
        all_files = sort_files(all_files, query.sort)

    # Get total count before pagination
    total = len(all_files)

    # Apply pagination
    paginated_files = all_files[query.offset : query.offset + query.limit]

    # Group if requested
    groups = None
    if query.group_by:
        groups = group_files(paginated_files, query.group_by)
        # Return empty files list when grouping
        return QueryResult(files=[], groups=groups, total=total, limit=query.limit, offset=query.offset)

    # Convert to dictionaries
    file_dicts = [file_to_dict(f) for f in paginated_files]

    return QueryResult(files=file_dicts, groups=groups, total=total, limit=query.limit, offset=query.offset)
