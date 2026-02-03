"""Git integration for automatic tracking."""

import logging
import os
from pathlib import Path

from git import InvalidGitRepositoryError, Repo

from codex.core.git_lock_manager import git_lock_manager

logger = logging.getLogger(__name__)


class GitManager:
    """Manager for Git operations in notebooks."""

    def __init__(self, notebook_path: str):
        # Resolve symlinks to ensure consistent path handling (e.g., /var -> /private/var on macOS)
        self.notebook_path = str(Path(notebook_path).resolve())
        self.repo: Repo
        self._init_or_get_repo()

    def _init_or_get_repo(self):
        """Initialize or get existing Git repository."""
        with git_lock_manager.lock(self.notebook_path):
            try:
                self.repo = Repo(self.notebook_path)
            except InvalidGitRepositoryError:
                # Initialize new repository
                self.repo = Repo.init(self.notebook_path)
                self._create_gitignore()

    def _create_gitignore(self):
        """Create .gitignore file with binary file patterns."""
        gitignore_path = os.path.join(self.notebook_path, ".gitignore")

        binary_patterns = [
            "# Binary files",
            "*.jpg",
            "*.jpeg",
            "*.png",
            "*.gif",
            "*.bmp",
            "*.ico",
            "*.pdf",
            "*.zip",
            "*.tar",
            "*.gz",
            "*.rar",
            "*.7z",
            "*.exe",
            "*.dll",
            "*.so",
            "*.dylib",
            "*.mp3",
            "*.mp4",
            "*.avi",
            "*.mov",
            "*.wmv",
            "",
            "# Codex metadata",
            ".codex/",
            "",
            "# System files",
            ".DS_Store",
            "Thumbs.db",
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".Python",
            "node_modules/",
            ".venv/",
            "venv/",
        ]

        with open(gitignore_path, "w") as f:
            f.write("\n".join(binary_patterns))

        # Add and commit .gitignore - save/restore cwd to avoid GitPython changing it
        original_cwd = None
        try:
            try:
                original_cwd = os.getcwd()
            except:
                pass

            self.repo.index.add([".gitignore"])
            self.repo.index.commit("Initialize .gitignore")
        finally:
            if original_cwd and os.path.exists(original_cwd):
                try:
                    os.chdir(original_cwd)
                except:
                    pass

    def is_binary_file(self, filepath: str) -> bool:
        """Check if a file should be excluded (binary)."""
        try:
            with open(filepath, "rb") as f:
                chunk = f.read(8192)
                return b"\0" in chunk
        except Exception:
            return False

    def add_file(self, filepath: str):
        """Add a file to Git if it's not binary."""
        if not self.repo:
            return

        # Resolve symlinks for consistent path handling
        resolved_path = str(Path(filepath).resolve())
        rel_path = os.path.relpath(resolved_path, self.notebook_path)

        # Check if file should be tracked
        if self.is_binary_file(filepath):
            return

        with git_lock_manager.lock(self.notebook_path):
            try:
                self.repo.index.add([rel_path])
            except Exception as e:
                logger.error(f"Error adding file to git: {e}")

    def commit(self, message: str, files: list[str] | None = None):
        """Commit changes to Git."""
        if not self.repo:
            return

        with git_lock_manager.lock(self.notebook_path):
            try:
                if files:
                    # Add specific files (resolve paths to handle symlinks like /var -> /private/var)
                    resolved_files = [str(Path(f).resolve()) for f in files]
                    rel_paths = [os.path.relpath(f, self.notebook_path) for f in resolved_files]
                    filtered_paths = [
                        p for p in rel_paths if not self.is_binary_file(os.path.join(self.notebook_path, p))
                    ]
                    if filtered_paths:
                        self.repo.index.add(filtered_paths)
                else:
                    # Add all tracked files
                    self.repo.git.add(A=True)

                # Only commit if there are changes
                if self.repo.index.diff("HEAD") or not self.repo.head.is_valid():
                    commit = self.repo.index.commit(message)
                    return commit.hexsha
            except Exception as e:
                logger.error(f"Error committing to git: {e}")
                return None

    def get_file_history(self, filepath: str, max_count: int = 10) -> list[dict]:
        """Get commit history for a specific file."""
        if not self.repo:
            return []

        resolved_path = str(Path(filepath).resolve())
        rel_path = os.path.relpath(resolved_path, self.notebook_path)

        with git_lock_manager.lock(self.notebook_path):
            try:
                commits = list(self.repo.iter_commits(paths=rel_path, max_count=max_count))
                history = []
                for commit in commits:
                    history.append(
                        {
                            "hash": commit.hexsha,
                            "author": str(commit.author),
                            "date": commit.committed_datetime.isoformat(),
                            "message": commit.message.strip(),
                        }
                    )
                return history
            except Exception as e:
                logger.error(f"Error getting file history: {e}")
                return []

    def get_file_at_commit(self, filepath: str, commit_hash: str) -> str | None:
        """Get file content at a specific commit."""
        if not self.repo:
            return None

        resolved_path = str(Path(filepath).resolve())
        rel_path = os.path.relpath(resolved_path, self.notebook_path)

        with git_lock_manager.lock(self.notebook_path):
            try:
                commit = self.repo.commit(commit_hash)
                blob = commit.tree / rel_path
                return blob.data_stream.read().decode("utf-8")
            except Exception as e:
                logger.error(f"Error getting file at commit: {e}")
                return None

    def auto_commit_on_change(self, filepath: str, sidecar: str | None = None) -> str | None:
        """Automatically commit a file when it changes."""
        if not self.repo:
            return

        resolved_path = str(Path(filepath).resolve())
        rel_path = os.path.relpath(resolved_path, self.notebook_path)
        filename = os.path.basename(filepath)

        with git_lock_manager.lock(self.notebook_path):
            if not self.is_binary_file(filepath):
                self.add_file(filepath)
            if sidecar:
                self.add_file(sidecar)
            commit_hash = self.commit(f"Auto-commit: {filename}")
            return commit_hash
