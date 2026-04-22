"""Background worker for processing staged zip imports."""

import asyncio
import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from codex.core.blocks import import_folder_as_pages
from codex.db.database import get_notebook_session, get_system_session_sync
from codex.db.models import Task

logger = logging.getLogger(__name__)


def _do_import(
    staging_dir: Path,
    notebook_path: Path,
    notebook_id: int,
    import_path: str,
    parent_path: str,
) -> dict:
    """Blocking import: move files from staging to notebook and create blocks."""
    logger.info(
        "zip import: starting move staging_dir=%s import_path=%s parent_path=%s",
        staging_dir,
        import_path,
        parent_path,
    )
    target_dir = notebook_path / parent_path if parent_path else notebook_path

    # Move extracted content from staging to the notebook directory
    src = staging_dir / import_path
    dest = target_dir / import_path.split("/")[-1] if "/" in import_path else target_dir / import_path

    # If the destination doesn't exist, move; otherwise merge
    if not dest.exists():
        shutil.move(str(src), str(dest))
        logger.info("zip import: moved src=%s -> dest=%s", src, dest)
    else:
        # Move contents into existing directory
        merged = 0
        renamed = 0
        for item in src.iterdir():
            item_dest = dest / item.name
            if not item_dest.exists():
                shutil.move(str(item), str(item_dest))
                merged += 1
            else:
                shutil.move(str(item), str(item_dest.parent / f"{item.stem}-imported{item.suffix}"))
                renamed += 1
        logger.info("zip import: merged into existing dir=%s merged=%d renamed=%d", dest, merged, renamed)

    # Compute the import path relative to notebook_path
    rel_import_path = str(dest.relative_to(notebook_path))

    nb_session = get_notebook_session(str(notebook_path))
    try:
        result = import_folder_as_pages(
            notebook_path=notebook_path,
            notebook_id=notebook_id,
            folder_path=rel_import_path,
            nb_session=nb_session,
        )
        return result
    finally:
        nb_session.close()


def _update_task(task_id: int, **kwargs) -> None:
    """Update task fields in the system database."""
    session = get_system_session_sync()
    try:
        task = session.get(Task, task_id)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            task.updated_at = datetime.now(UTC)
            session.add(task)
            session.commit()
    finally:
        session.close()


async def process_zip_import(
    task_id: int,
    staging_dir: Path,
    notebook_path: Path,
    notebook_id: int,
    import_path: str,
    parent_path: str,
) -> None:
    """Process a staged zip import in the background."""
    try:
        logger.info("zip import: task %s in_progress (import_path=%s)", task_id, import_path)
        _update_task(task_id, status="in_progress")

        result = await asyncio.to_thread(
            _do_import, staging_dir, notebook_path, notebook_id, import_path, parent_path
        )

        meta = json.dumps({
            "pages_created": result.get("pages_created", 0),
            "blocks_created": result.get("blocks_created", 0),
            "path": result.get("path", ""),
        })
        _update_task(
            task_id,
            status="completed",
            task_metadata=meta,
            completed_at=datetime.now(UTC),
        )
        logger.info(f"Zip import task {task_id} completed: {result}")

    except Exception as e:
        logger.error(f"Zip import task {task_id} failed: {e}", exc_info=True)
        _update_task(
            task_id,
            status="failed",
            task_metadata=json.dumps({"error": str(e)}),
        )

    finally:
        # Clean up staging directory
        try:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up staging dir {staging_dir}: {e}")
