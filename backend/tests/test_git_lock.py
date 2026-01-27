"""Tests for git lock manager to ensure concurrent operations don't conflict."""

import pytest
import tempfile
import threading
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from codex.core.git_manager import GitManager
from codex.core.git_lock_manager import git_lock_manager


@pytest.fixture
def temp_notebook():
    """Create a temporary directory for notebook tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    import shutil

    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
    # Clear locks for this path
    try:
        git_lock_manager.clear_locks(str(Path(temp_dir).resolve()))
    except Exception:
        pass


@pytest.fixture
def initialized_notebook(temp_notebook):
    """Create and initialize a notebook with git."""
    git_manager = GitManager(temp_notebook)
    # Create a sample file
    test_file = os.path.join(temp_notebook, "test.md")
    with open(test_file, "w") as f:
        f.write("# Initial content\n")
    git_manager.commit("Initial commit", [test_file])
    return temp_notebook


def test_git_lock_manager_singleton():
    """Test that GitLockManager is a singleton."""
    from codex.core.git_lock_manager import GitLockManager

    manager1 = GitLockManager()
    manager2 = GitLockManager()
    assert manager1 is manager2


def test_concurrent_commits_same_notebook(initialized_notebook):
    """Test that concurrent commits to the same notebook are serialized."""
    results = []
    errors = []

    def commit_file(file_number):
        """Create and commit a file."""
        try:
            file_path = os.path.join(initialized_notebook, f"file_{file_number}.md")
            with open(file_path, "w") as f:
                f.write(f"# File {file_number}\nContent for file {file_number}\n")

            git_manager = GitManager(initialized_notebook)
            commit_hash = git_manager.commit(f"Add file {file_number}", [file_path])
            results.append((file_number, commit_hash))
        except Exception as e:
            errors.append((file_number, str(e)))

    # Run 10 concurrent commits
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(commit_file, i) for i in range(10)]
        for future in as_completed(futures):
            future.result()  # Wait for completion

    # All commits should succeed
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == 10

    # All commit hashes should be unique (each commit was separate)
    commit_hashes = [r[1] for r in results if r[1] is not None]
    assert len(commit_hashes) == len(set(commit_hashes))


def test_concurrent_add_and_commit(initialized_notebook):
    """Test concurrent add and commit operations."""
    results = []
    errors = []

    def add_and_commit(file_number):
        """Add a file and commit."""
        try:
            file_path = os.path.join(initialized_notebook, f"concurrent_{file_number}.md")
            with open(file_path, "w") as f:
                f.write(f"# Concurrent {file_number}\n")

            git_manager = GitManager(initialized_notebook)
            git_manager.add_file(file_path)
            time.sleep(0.01)  # Small delay to increase chance of conflict
            commit_hash = git_manager.commit(f"Concurrent commit {file_number}")
            results.append((file_number, commit_hash))
        except Exception as e:
            errors.append((file_number, str(e)))

    # Run 5 concurrent add/commit operations
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(add_and_commit, i) for i in range(5)]
        for future in as_completed(futures):
            future.result()

    # Should not have any errors
    assert len(errors) == 0, f"Errors occurred: {errors}"


def test_concurrent_reads_and_writes(initialized_notebook):
    """Test that reads and writes can happen concurrently without errors."""
    # Create some initial files
    for i in range(3):
        file_path = os.path.join(initialized_notebook, f"read_test_{i}.md")
        with open(file_path, "w") as f:
            f.write(f"# Read Test {i}\n")

    git_manager = GitManager(initialized_notebook)
    git_manager.commit("Initial files for read test")

    results = {"reads": [], "writes": []}
    errors = []

    def read_history(file_number):
        """Read file history."""
        try:
            file_path = os.path.join(initialized_notebook, f"read_test_{file_number}.md")
            git_manager = GitManager(initialized_notebook)
            history = git_manager.get_file_history(file_path)
            results["reads"].append((file_number, len(history)))
        except Exception as e:
            errors.append(("read", file_number, str(e)))

    def write_file(file_number):
        """Write and commit a new file."""
        try:
            file_path = os.path.join(initialized_notebook, f"write_test_{file_number}.md")
            with open(file_path, "w") as f:
                f.write(f"# Write Test {file_number}\n")

            git_manager = GitManager(initialized_notebook)
            commit_hash = git_manager.commit(f"Write test {file_number}", [file_path])
            results["writes"].append((file_number, commit_hash))
        except Exception as e:
            errors.append(("write", file_number, str(e)))

    # Run mixed read and write operations
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for i in range(3):
            futures.append(executor.submit(read_history, i % 3))
            futures.append(executor.submit(write_file, i))

        for future in as_completed(futures):
            future.result()

    # Should not have any errors
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results["reads"]) >= 3
    assert len(results["writes"]) >= 3


def test_auto_commit_concurrent(initialized_notebook):
    """Test concurrent auto-commits don't conflict."""
    results = []
    errors = []

    def auto_commit_file(file_number):
        """Create a file and auto-commit it."""
        try:
            file_path = os.path.join(initialized_notebook, f"auto_{file_number}.md")
            with open(file_path, "w") as f:
                f.write(f"# Auto {file_number}\n")

            git_manager = GitManager(initialized_notebook)
            commit_hash = git_manager.auto_commit_on_change(file_path)
            results.append((file_number, commit_hash))
        except Exception as e:
            errors.append((file_number, str(e)))

    # Simulate file watcher auto-commits
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(auto_commit_file, i) for i in range(5)]
        for future in as_completed(futures):
            future.result()

    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == 5


def test_lock_per_notebook_isolation():
    """Test that locks are isolated per notebook path."""
    temp_dir1 = tempfile.mkdtemp()
    temp_dir2 = tempfile.mkdtemp()

    try:
        # Initialize two separate notebooks
        git_manager1 = GitManager(temp_dir1)
        git_manager2 = GitManager(temp_dir2)

        results = []

        def commit_to_notebook(notebook_path, file_name):
            """Commit to a specific notebook."""
            file_path = os.path.join(notebook_path, file_name)
            with open(file_path, "w") as f:
                f.write(f"Content for {file_name}\n")

            git_manager = GitManager(notebook_path)
            commit_hash = git_manager.commit(f"Add {file_name}", [file_path])
            results.append((notebook_path, file_name, commit_hash))

        # Operations on different notebooks should not block each other
        # (though they might due to threading, they shouldn't deadlock)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(commit_to_notebook, temp_dir1, "file1.md"),
                executor.submit(commit_to_notebook, temp_dir1, "file2.md"),
                executor.submit(commit_to_notebook, temp_dir2, "file1.md"),
                executor.submit(commit_to_notebook, temp_dir2, "file2.md"),
            ]
            for future in as_completed(futures):
                future.result()

        # All operations should complete successfully
        assert len(results) == 4

    finally:
        import shutil

        shutil.rmtree(temp_dir1, ignore_errors=True)
        shutil.rmtree(temp_dir2, ignore_errors=True)
        git_lock_manager.clear_locks(temp_dir1)
        git_lock_manager.clear_locks(temp_dir2)


def test_nested_lock_acquisition(initialized_notebook):
    """Test that nested lock acquisition works (RLock behavior)."""
    git_manager = GitManager(initialized_notebook)

    # This should not deadlock because we use RLock
    file_path = os.path.join(initialized_notebook, "nested_test.md")
    with open(file_path, "w") as f:
        f.write("# Nested test\n")

    # auto_commit_on_change internally calls add_file and commit,
    # which all try to acquire the lock - this tests nested locking
    commit_hash = git_manager.auto_commit_on_change(file_path)

    assert commit_hash is not None


def test_concurrent_init_same_path():
    """Test that concurrent initialization of GitManager for same path is safe."""
    temp_dir = tempfile.mkdtemp()

    # Create a dummy file so the directory exists
    dummy_file = os.path.join(temp_dir, "dummy.txt")
    with open(dummy_file, "w") as f:
        f.write("dummy")

    try:
        managers = []
        errors = []

        def init_manager():
            """Initialize a GitManager."""
            try:
                # Save and restore cwd to avoid issues with Git changing it
                original_cwd = None
                try:
                    original_cwd = os.getcwd()
                except:
                    pass

                try:
                    manager = GitManager(temp_dir)
                    managers.append(manager)
                finally:
                    if original_cwd and os.path.exists(original_cwd):
                        try:
                            os.chdir(original_cwd)
                        except:
                            pass
            except Exception as e:
                errors.append(str(e))

        # Multiple threads trying to initialize the same repo
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(init_manager) for _ in range(5)]
            for future in as_completed(futures):
                future.result()

        # All should succeed without errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(managers) == 5

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        git_lock_manager.clear_locks(temp_dir)
