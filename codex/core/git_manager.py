"""Git operations manager for Lab Notebook."""

import json
from pathlib import Path
from typing import Optional

try:
    from git import Repo
    from git.exc import InvalidGitRepositoryError

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class GitManager:
    """Manager for Git operations on notebook structure."""

    def __init__(self, git_path: Path):
        """Initialize the Git manager."""
        self.git_path = git_path
        self.repo: Optional[Repo] = None

    @classmethod
    def initialize(cls, git_path: Path) -> "GitManager":
        """Initialize a new Git repository."""
        manager = cls(git_path)
        manager._init_repo()
        return manager

    def _init_repo(self):
        """Initialize or load the Git repository."""
        if not GIT_AVAILABLE:
            return

        self.git_path.mkdir(parents=True, exist_ok=True)

        try:
            self.repo = Repo(self.git_path)
        except InvalidGitRepositoryError:
            self.repo = Repo.init(self.git_path)

            # Create initial structure
            notebooks_dir = self.git_path / "notebooks"
            notebooks_dir.mkdir(exist_ok=True)

            # Create .gitkeep
            gitkeep = notebooks_dir / ".gitkeep"
            gitkeep.touch()

            # Initial commit
            self.repo.index.add([str(gitkeep.relative_to(self.git_path))])
            self.repo.index.commit("Initialize lab notebook repository")

    def load(self):
        """Load an existing Git repository."""
        if not GIT_AVAILABLE:
            return

        if self.git_path.exists():
            try:
                self.repo = Repo(self.git_path)
            except InvalidGitRepositoryError:
                self._init_repo()

    def create_notebook(self, notebook_id: str, notebook_data: dict):
        """Create a notebook in Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        notebook_dir = self.git_path / "notebooks" / notebook_id
        notebook_dir.mkdir(parents=True, exist_ok=True)

        # Write meta.json
        meta_path = notebook_dir / "meta.json"
        with open(meta_path, "w") as f:
            json.dump(notebook_data, f, indent=2, default=str)

        # Create pages directory
        pages_dir = notebook_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        (pages_dir / ".gitkeep").touch()

        # Commit
        self.repo.index.add([
            str(meta_path.relative_to(self.git_path)),
            str((pages_dir / ".gitkeep").relative_to(self.git_path)),
        ])
        self.repo.index.commit(f"Create notebook: {notebook_data.get('title', notebook_id)}")

    def update_notebook(self, notebook_id: str, notebook_data: dict):
        """Update a notebook in Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        meta_path = self.git_path / "notebooks" / notebook_id / "meta.json"
        if meta_path.exists():
            with open(meta_path, "w") as f:
                json.dump(notebook_data, f, indent=2, default=str)

            self.repo.index.add([str(meta_path.relative_to(self.git_path))])
            self.repo.index.commit(f"Update notebook: {notebook_data.get('title', notebook_id)}")

    def delete_notebook(self, notebook_id: str):
        """Delete a notebook from Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        notebook_dir = self.git_path / "notebooks" / notebook_id
        if notebook_dir.exists():
            # Remove all files in the directory
            for item in notebook_dir.rglob("*"):
                if item.is_file():
                    self.repo.index.remove([str(item.relative_to(self.git_path))])

            self.repo.index.commit(f"Delete notebook: {notebook_id}")

    def create_page(self, notebook_id: str, page_id: str, page_data: dict):
        """Create a page in Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        page_dir = self.git_path / "notebooks" / notebook_id / "pages" / page_id
        page_dir.mkdir(parents=True, exist_ok=True)

        # Write meta.json
        meta_path = page_dir / "meta.json"
        with open(meta_path, "w") as f:
            json.dump(page_data, f, indent=2, default=str)

        # Create entries directory
        entries_dir = page_dir / "entries"
        entries_dir.mkdir(exist_ok=True)
        (entries_dir / ".gitkeep").touch()

        # Commit
        self.repo.index.add([
            str(meta_path.relative_to(self.git_path)),
            str((entries_dir / ".gitkeep").relative_to(self.git_path)),
        ])
        self.repo.index.commit(f"Create page: {page_data.get('title', page_id)}")

    def update_page(self, notebook_id: str, page_id: str, page_data: dict):
        """Update a page in Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        meta_path = self.git_path / "notebooks" / notebook_id / "pages" / page_id / "meta.json"
        if meta_path.exists():
            with open(meta_path, "w") as f:
                json.dump(page_data, f, indent=2, default=str)

            self.repo.index.add([str(meta_path.relative_to(self.git_path))])
            self.repo.index.commit(f"Update page: {page_data.get('title', page_id)}")

    def delete_page(self, notebook_id: str, page_id: str):
        """Delete a page from Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        page_dir = self.git_path / "notebooks" / notebook_id / "pages" / page_id
        if page_dir.exists():
            for item in page_dir.rglob("*"):
                if item.is_file():
                    self.repo.index.remove([str(item.relative_to(self.git_path))])

            self.repo.index.commit(f"Delete page: {page_id}")

    def commit_entry(self, notebook_id: str, page_id: str, entry_id: str, entry_data: dict):
        """Commit an entry to Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        entry_path = (
            self.git_path / "notebooks" / notebook_id / "pages" / page_id / "entries" / f"{entry_id}.json"
        )
        entry_path.parent.mkdir(parents=True, exist_ok=True)

        with open(entry_path, "w") as f:
            json.dump(entry_data, f, indent=2, default=str)

        self.repo.index.add([str(entry_path.relative_to(self.git_path))])
        self.repo.index.commit(f"Add entry: {entry_data.get('title', entry_id)}")

    def update_entry(self, notebook_id: str, page_id: str, entry_id: str, entry_data: dict):
        """Update an entry in Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        entry_path = (
            self.git_path / "notebooks" / notebook_id / "pages" / page_id / "entries" / f"{entry_id}.json"
        )

        if entry_path.exists():
            with open(entry_path, "w") as f:
                json.dump(entry_data, f, indent=2, default=str)

            self.repo.index.add([str(entry_path.relative_to(self.git_path))])
            self.repo.index.commit(f"Update entry: {entry_data.get('title', entry_id)}")

    def delete_entry(self, notebook_id: str, page_id: str, entry_id: str):
        """Delete an entry from Git."""
        if not GIT_AVAILABLE or not self.repo:
            return

        entry_path = (
            self.git_path / "notebooks" / notebook_id / "pages" / page_id / "entries" / f"{entry_id}.json"
        )

        if entry_path.exists():
            self.repo.index.remove([str(entry_path.relative_to(self.git_path))])
            self.repo.index.commit(f"Delete entry: {entry_id}")
