#!/usr/bin/env python3.12
"""Test script to verify git integration in notebooks."""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, '/home/user/codex')

from backend.core.git_manager import GitManager


def test_git_manager():
    """Test GitManager functionality."""
    print("Testing GitManager...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        notebook_path = tmpdir
        print(f"Created test directory: {notebook_path}")

        # Test 1: Initialize git repo
        print("\n1. Testing git repo initialization...")
        git_manager = GitManager(notebook_path)

        # Check that .git directory exists
        git_dir = Path(notebook_path) / ".git"
        assert git_dir.exists(), ".git directory should exist"
        print("✓ Git repo initialized successfully")

        # Check that .gitignore exists
        gitignore_path = Path(notebook_path) / ".gitignore"
        assert gitignore_path.exists(), ".gitignore should exist"
        print("✓ .gitignore created successfully")

        # Test 2: Create and commit a file
        print("\n2. Testing file creation and commit...")
        test_file = Path(notebook_path) / "test.md"
        test_file.write_text("# Test File\n\nThis is a test file.")

        commit_hash = git_manager.commit("Add test file", [str(test_file)])
        assert commit_hash is not None, "Commit should return a hash"
        print(f"✓ File committed successfully with hash: {commit_hash[:8]}")

        # Test 3: Update file and commit again
        print("\n3. Testing file update and commit...")
        test_file.write_text("# Test File\n\nThis is an updated test file.")

        commit_hash2 = git_manager.commit("Update test file", [str(test_file)])
        assert commit_hash2 is not None, "Second commit should return a hash"
        assert commit_hash2 != commit_hash, "Second commit should have different hash"
        print(f"✓ File updated and committed successfully with hash: {commit_hash2[:8]}")

        # Test 4: Get file history
        print("\n4. Testing file history...")
        history = git_manager.get_file_history(str(test_file))
        assert len(history) == 2, "Should have 2 commits in history"
        print(f"✓ File history retrieved successfully: {len(history)} commits")

        # Test 5: Test binary file exclusion
        print("\n5. Testing binary file exclusion...")
        binary_file = Path(notebook_path) / "test.jpg"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")  # Fake PNG header

        assert git_manager.is_binary_file(str(binary_file)), "Should detect binary file"
        print("✓ Binary file detection works")

        # Test 6: Auto-commit
        print("\n6. Testing auto-commit...")
        auto_file = Path(notebook_path) / "auto.txt"
        auto_file.write_text("Auto-committed file")

        auto_hash = git_manager.auto_commit_on_change(str(auto_file))
        assert auto_hash is not None, "Auto-commit should return a hash"
        print(f"✓ Auto-commit successful with hash: {auto_hash[:8]}")

        print("\n" + "="*60)
        print("All tests passed! ✓")
        print("="*60)


if __name__ == "__main__":
    try:
        test_git_manager()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
