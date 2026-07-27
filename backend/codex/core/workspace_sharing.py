"""Shared/personal workspace classification (design doc §1, §3.5).

Split out of `codex.core.s3_indexer` so modules that need this check (git
demotion, notebook/watcher startup) don't have to import the indexer itself
-- `s3_indexer` already imports `codex.core.watcher`, and `watcher` needs
this check too, which would otherwise be a cycle.
"""

from __future__ import annotations

from codex.db.models import Workspace


def is_shared_workspace(workspace: Workspace) -> bool:
    """Org workspaces are S3-synced (shared); personal workspaces are not (design doc §1)."""
    return workspace.org_id is not None
