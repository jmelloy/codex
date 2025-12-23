"""Git integration for automatic tracking."""

import os
from pathlib import Path
from typing import Optional, List
import git
from git import Repo, InvalidGitRepositoryError


class GitManager:
    """Manager for Git operations in notebooks."""
    
    def __init__(self, notebook_path: str):
        self.notebook_path = notebook_path
        self.repo: Optional[Repo] = None
        self._init_or_get_repo()
    
    def _init_or_get_repo(self):
        """Initialize or get existing Git repository."""
        try:
            self.repo = Repo(self.notebook_path)
        except InvalidGitRepositoryError:
            # Initialize new repository
            self.repo = Repo.init(self.notebook_path)
            self._create_gitignore()
    
    def _create_gitignore(self):
        """Create .gitignore file with binary file patterns."""
        gitignore_path = os.path.join(self.notebook_path, '.gitignore')
        
        binary_patterns = [
            '# Binary files',
            '*.jpg',
            '*.jpeg',
            '*.png',
            '*.gif',
            '*.bmp',
            '*.ico',
            '*.pdf',
            '*.zip',
            '*.tar',
            '*.gz',
            '*.rar',
            '*.7z',
            '*.exe',
            '*.dll',
            '*.so',
            '*.dylib',
            '*.mp3',
            '*.mp4',
            '*.avi',
            '*.mov',
            '*.wmv',
            '',
            '# Codex metadata',
            '.codex/',
            '',
            '# System files',
            '.DS_Store',
            'Thumbs.db',
            '__pycache__/',
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '.Python',
            'node_modules/',
            '.venv/',
            'venv/',
        ]
        
        with open(gitignore_path, 'w') as f:
            f.write('\n'.join(binary_patterns))
        
        # Add and commit .gitignore
        self.repo.index.add(['.gitignore'])
        self.repo.index.commit('Initialize .gitignore')
    
    def is_binary_file(self, filepath: str) -> bool:
        """Check if a file should be excluded (binary)."""
        try:
            with open(filepath, 'rb') as f:
                chunk = f.read(8192)
                return b'\0' in chunk
        except Exception:
            return False
    
    def add_file(self, filepath: str):
        """Add a file to Git if it's not binary."""
        if not self.repo:
            return
        
        rel_path = os.path.relpath(filepath, self.notebook_path)
        
        # Check if file should be tracked
        if self.is_binary_file(filepath):
            return
        
        try:
            self.repo.index.add([rel_path])
        except Exception as e:
            print(f"Error adding file to git: {e}")
    
    def commit(self, message: str, files: Optional[List[str]] = None):
        """Commit changes to Git."""
        if not self.repo:
            return
        
        try:
            if files:
                # Add specific files
                rel_paths = [os.path.relpath(f, self.notebook_path) for f in files]
                filtered_paths = [p for p in rel_paths if not self.is_binary_file(
                    os.path.join(self.notebook_path, p)
                )]
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
            print(f"Error committing to git: {e}")
            return None
    
    def get_file_history(self, filepath: str, max_count: int = 10) -> List[dict]:
        """Get commit history for a specific file."""
        if not self.repo:
            return []
        
        rel_path = os.path.relpath(filepath, self.notebook_path)
        
        try:
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=max_count))
            history = []
            for commit in commits:
                history.append({
                    'hash': commit.hexsha,
                    'author': str(commit.author),
                    'date': commit.committed_datetime.isoformat(),
                    'message': commit.message.strip()
                })
            return history
        except Exception as e:
            print(f"Error getting file history: {e}")
            return []
    
    def get_file_at_commit(self, filepath: str, commit_hash: str) -> Optional[str]:
        """Get file content at a specific commit."""
        if not self.repo:
            return None
        
        rel_path = os.path.relpath(filepath, self.notebook_path)
        
        try:
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / rel_path
            return blob.data_stream.read().decode('utf-8')
        except Exception as e:
            print(f"Error getting file at commit: {e}")
            return None
    
    def get_diff(self, filepath: str, commit_hash1: str, commit_hash2: str = "HEAD") -> Optional[str]:
        """Get diff between two commits for a file."""
        if not self.repo:
            return None
        
        rel_path = os.path.relpath(filepath, self.notebook_path)
        
        try:
            commit1 = self.repo.commit(commit_hash1)
            commit2 = self.repo.commit(commit_hash2)
            diff = commit1.diff(commit2, paths=rel_path, create_patch=True)
            if diff:
                return diff[0].diff.decode('utf-8')
            return None
        except Exception as e:
            print(f"Error getting diff: {e}")
            return None
    
    def auto_commit_on_change(self, filepath: str):
        """Automatically commit a file when it changes."""
        if not self.repo:
            return
        
        rel_path = os.path.relpath(filepath, self.notebook_path)
        filename = os.path.basename(filepath)
        
        # Don't commit binary files
        if self.is_binary_file(filepath):
            return
        
        self.add_file(filepath)
        commit_hash = self.commit(f"Auto-commit: {filename}")
        return commit_hash
