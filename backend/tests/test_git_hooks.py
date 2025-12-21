"""Tests for git hooks and daily notes functionality."""

from datetime import datetime
from pathlib import Path

import pytest
from core.git_hooks import DailyNoteManager, GitHookManager


class TestGitHookManager:
    """Tests for GitHookManager."""

    def test_generate_post_commit_script_without_workspace(self):
        """Test generating post-commit script without workspace."""
        script = GitHookManager._generate_post_commit_script()
        assert "#!/bin/sh" in script
        assert "codex daily-note add-commit" in script
        assert "--workspace" not in script

    def test_generate_post_commit_script_with_workspace(self):
        """Test generating post-commit script with workspace."""
        workspace = Path("/home/user/workspace")
        script = GitHookManager._generate_post_commit_script(workspace)
        assert "#!/bin/sh" in script
        assert "codex daily-note add-commit" in script
        assert f'--workspace "{workspace}"' in script

    def test_install_post_commit_hook(self, tmp_path):
        """Test installing post-commit hook."""
        hooks_path = tmp_path / "hooks"
        success = GitHookManager.install_post_commit_hook(hooks_path)
        assert success

        post_commit = hooks_path / "post-commit"
        assert post_commit.exists()
        assert post_commit.is_file()
        # Check if executable
        assert post_commit.stat().st_mode & 0o111

    def test_install_post_commit_hook_with_workspace(self, tmp_path):
        """Test installing post-commit hook with workspace."""
        hooks_path = tmp_path / "hooks"
        workspace = tmp_path / "workspace"
        success = GitHookManager.install_post_commit_hook(hooks_path, workspace)
        assert success

        post_commit = hooks_path / "post-commit"
        content = post_commit.read_text()
        assert f'--workspace "{workspace}"' in content

    def test_uninstall_post_commit_hook(self, tmp_path):
        """Test uninstalling post-commit hook."""
        hooks_path = tmp_path / "hooks"
        # Install first
        GitHookManager.install_post_commit_hook(hooks_path)
        assert (hooks_path / "post-commit").exists()

        # Uninstall
        success = GitHookManager.uninstall_post_commit_hook(hooks_path)
        assert success
        assert not (hooks_path / "post-commit").exists()

    def test_uninstall_nonexistent_hook(self, tmp_path):
        """Test uninstalling a hook that doesn't exist."""
        hooks_path = tmp_path / "hooks"
        success = GitHookManager.uninstall_post_commit_hook(hooks_path)
        assert success  # Should succeed even if hook doesn't exist


class TestDailyNoteManager:
    """Tests for DailyNoteManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a DailyNoteManager for testing."""
        return DailyNoteManager(tmp_path)

    def test_daily_notes_path_created(self, manager):
        """Test that daily notes directory is created."""
        assert manager.daily_notes_path.exists()
        assert manager.daily_notes_path.is_dir()

    def test_get_daily_note_path_default(self, manager):
        """Test getting today's daily note path."""
        note_path = manager.get_daily_note_path()
        today = datetime.now().strftime("%Y-%m-%d")
        assert note_path.name == f"{today}.md"
        assert note_path.parent == manager.daily_notes_path

    def test_get_daily_note_path_custom_date(self, manager):
        """Test getting daily note path for custom date."""
        date = datetime(2024, 12, 20)
        note_path = manager.get_daily_note_path(date)
        assert note_path.name == "2024-12-20.md"
        assert note_path.parent == manager.daily_notes_path

    def test_create_daily_note(self, manager):
        """Test creating a daily note."""
        note_path = manager.create_daily_note()
        assert note_path.exists()

        content = note_path.read_text()
        assert "---" in content
        assert "title:" in content
        assert "date:" in content
        assert "# Daily Note" in content
        assert "## Notes" in content
        assert "## Commits" in content
        assert "## Tasks" in content

    def test_create_daily_note_custom_date(self, manager):
        """Test creating a daily note for custom date."""
        date = datetime(2024, 12, 20)
        note_path = manager.create_daily_note(date)
        assert note_path.exists()

        content = note_path.read_text()
        assert "2024-12-20" in content

    def test_create_daily_note_idempotent(self, manager):
        """Test that creating existing daily note doesn't overwrite."""
        note_path = manager.create_daily_note()
        original_content = note_path.read_text()

        # Try to create again
        note_path2 = manager.create_daily_note()
        assert note_path == note_path2
        assert note_path.read_text() == original_content

    def test_add_commit_entry_to_new_note(self, manager):
        """Test adding commit entry to a new daily note."""
        note_path = manager.add_commit_entry(
            commit_sha="abc123def456",
            commit_message="Test commit",
            branch="main",
            repo="test-repo",
        )
        assert note_path.exists()

        content = note_path.read_text()
        assert "::: commit" in content
        assert "abc123de" in content  # Shortened SHA
        assert "Test commit" in content
        assert "main" in content
        assert "test-repo" in content

    def test_add_commit_entry_to_existing_note(self, manager):
        """Test adding commit entry to existing daily note."""
        # Create initial note with first commit
        manager.add_commit_entry(
            commit_sha="abc123",
            commit_message="First commit",
            branch="main",
            repo="repo1",
        )

        # Add second commit
        note_path = manager.add_commit_entry(
            commit_sha="def456",
            commit_message="Second commit",
            branch="feature",
            repo="repo2",
        )

        content = note_path.read_text()
        assert content.count("::: commit") == 2
        assert "First commit" in content
        assert "Second commit" in content
        assert "abc123" in content
        assert "def456" in content

    def test_add_commit_entry_custom_date(self, manager):
        """Test adding commit entry for custom date."""
        date = datetime(2024, 12, 20)
        note_path = manager.add_commit_entry(
            commit_sha="abc123",
            commit_message="Test commit",
            branch="main",
            repo="test-repo",
            date=date,
        )
        assert "2024-12-20" in note_path.name

        content = note_path.read_text()
        assert "2024-12-20" in content

    def test_list_daily_notes_empty(self, manager):
        """Test listing daily notes when none exist."""
        notes = manager.list_daily_notes()
        assert notes == []

    def test_list_daily_notes_single(self, manager):
        """Test listing daily notes with one note."""
        manager.create_daily_note()
        notes = manager.list_daily_notes()
        assert len(notes) == 1
        assert notes[0].suffix == ".md"

    def test_list_daily_notes_multiple(self, manager):
        """Test listing multiple daily notes in reverse chronological order."""
        # Create notes for different dates
        dates = [
            datetime(2024, 12, 18),
            datetime(2024, 12, 20),
            datetime(2024, 12, 19),
        ]
        for date in dates:
            manager.create_daily_note(date)

        notes = manager.list_daily_notes()
        assert len(notes) == 3

        # Should be in reverse chronological order
        assert "2024-12-20" in notes[0].name
        assert "2024-12-19" in notes[1].name
        assert "2024-12-18" in notes[2].name

    def test_list_daily_notes_with_limit(self, manager):
        """Test listing daily notes with limit."""
        # Create 5 notes
        for i in range(5):
            date = datetime(2024, 12, 20 - i)
            manager.create_daily_note(date)

        notes = manager.list_daily_notes(limit=3)
        assert len(notes) == 3

        # Should be most recent 3
        assert "2024-12-20" in notes[0].name
        assert "2024-12-19" in notes[1].name
        assert "2024-12-18" in notes[2].name


class TestDailyNoteFormat:
    """Tests for daily note format and structure."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a DailyNoteManager for testing."""
        return DailyNoteManager(tmp_path)

    def test_frontmatter_format(self, manager):
        """Test that daily note has correct frontmatter format."""
        note_path = manager.create_daily_note()
        content = note_path.read_text()

        # Check frontmatter delimiters
        lines = content.split("\n")
        assert lines[0] == "---"
        assert "---" in lines[1:10]  # Should close within first 10 lines

        # Check required frontmatter fields
        assert any("title:" in line for line in lines[:10])
        assert any("date:" in line for line in lines[:10])
        assert any("tags:" in line for line in lines[:10])

    def test_commit_block_format(self, manager):
        """Test that commit blocks have correct format."""
        manager.add_commit_entry(
            commit_sha="abc123def456",
            commit_message="Test commit message",
            branch="main",
            repo="test-repo",
        )
        note_path = manager.get_daily_note_path()
        content = note_path.read_text()

        # Check block delimiters
        assert "::: commit" in content
        assert ":::" in content

        # Check commit details
        assert "**Time**:" in content
        assert "**Repo**:" in content
        assert "**Branch**:" in content
        assert "**SHA**:" in content
        assert "**Message**:" in content

    def test_markdown_structure(self, manager):
        """Test overall markdown structure."""
        note_path = manager.create_daily_note()
        content = note_path.read_text()

        # Check main sections
        assert "# Daily Note" in content
        assert "## Notes" in content
        assert "## Commits" in content
        assert "## Tasks" in content

        # Check task list format
        assert "- [ ]" in content


class TestWindowLogging:
    """Tests for window logging functionality."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a DailyNoteManager for testing."""
        return DailyNoteManager(tmp_path)

    def test_add_window_entry_to_new_note(self, manager):
        """Test adding window entry to a new daily note."""
        note_path = manager.add_window_entry(
            app_name="Safari",
            window_name="GitHub - Pull Requests",
            url="https://github.com/pulls",
        )
        assert note_path.exists()

        content = note_path.read_text()
        assert "::: window" in content
        assert "Safari" in content
        assert "GitHub - Pull Requests" in content
        assert "https://github.com/pulls" in content

    def test_add_window_entry_without_url(self, manager):
        """Test adding window entry without URL."""
        note_path = manager.add_window_entry(
            app_name="Visual Studio Code",
            window_name="main.py - myproject",
        )
        assert note_path.exists()

        content = note_path.read_text()
        assert "::: window" in content
        assert "Visual Studio Code" in content
        assert "main.py - myproject" in content
        assert "**URL**:" not in content

    def test_add_window_entry_to_existing_note(self, manager):
        """Test adding window entry to existing daily note."""
        # Create initial note with first window
        manager.add_window_entry(
            app_name="Safari",
            window_name="First Window",
        )

        # Add second window
        note_path = manager.add_window_entry(
            app_name="Chrome",
            window_name="Second Window",
            url="https://example.com",
        )

        content = note_path.read_text()
        assert content.count("::: window") == 2
        assert "First Window" in content
        assert "Second Window" in content
        assert "Safari" in content
        assert "Chrome" in content

    def test_add_window_entry_creates_active_windows_section(self, manager):
        """Test that window entry creates Active Windows section."""
        note_path = manager.add_window_entry(
            app_name="Terminal",
            window_name="bash",
        )

        content = note_path.read_text()
        assert "## Active Windows" in content

    def test_add_window_entry_before_commits_section(self, manager):
        """Test that Active Windows section is added before Commits."""
        # Create note with commit first
        manager.add_commit_entry(
            commit_sha="abc123",
            commit_message="Test commit",
            branch="main",
            repo="test-repo",
        )

        # Add window entry
        note_path = manager.add_window_entry(
            app_name="Terminal",
            window_name="bash",
        )

        content = note_path.read_text()

        # Active Windows should come before Commits
        windows_pos = content.find("## Active Windows")
        commits_pos = content.find("## Commits")
        assert windows_pos < commits_pos

    def test_window_entry_format(self, manager):
        """Test that window entry has correct format."""
        manager.add_window_entry(
            app_name="Safari",
            window_name="GitHub",
            url="https://github.com",
        )
        note_path = manager.get_daily_note_path()
        content = note_path.read_text()

        # Check block delimiters
        assert "::: window" in content
        assert ":::" in content

        # Check window details
        assert "**Time**:" in content
        assert "**App**:" in content
        assert "**Window**:" in content
        assert "**URL**:" in content

    def test_multiple_window_entries_same_day(self, manager):
        """Test adding multiple window entries on same day."""
        apps = [
            ("Safari", "GitHub", "https://github.com"),
            ("Visual Studio Code", "main.py", None),
            ("Terminal", "bash", None),
            ("Chrome", "Google", "https://google.com"),
        ]

        for app_name, window_name, url in apps:
            manager.add_window_entry(app_name, window_name, url)

        note_path = manager.get_daily_note_path()
        content = note_path.read_text()

        # Should have all 4 window entries
        assert content.count("::: window") == 4
        for app_name, window_name, url in apps:
            assert app_name in content
            assert window_name in content
            if url:
                assert url in content

    def test_window_entry_with_multiple_sections(self, manager):
        """Test that window entries are correctly placed with multiple sections."""
        # Create note with multiple sections
        manager.create_daily_note()

        # Add a commit
        manager.add_commit_entry(
            commit_sha="abc123",
            commit_message="Test commit",
            branch="main",
            repo="test-repo",
        )

        # Add window entry (should go before commits)
        manager.add_window_entry(
            app_name="Terminal",
            window_name="bash",
        )

        # Add another window entry
        manager.add_window_entry(
            app_name="Safari",
            window_name="GitHub",
            url="https://github.com",
        )

        note_path = manager.get_daily_note_path()
        content = note_path.read_text()

        # Verify all sections exist in the correct order
        notes_pos = content.find("## Notes")
        windows_pos = content.find("## Active Windows")
        commits_pos = content.find("## Commits")
        tasks_pos = content.find("## Tasks")

        # All sections should exist
        assert notes_pos > 0
        assert windows_pos > 0
        assert commits_pos > 0
        assert tasks_pos > 0

        # Verify order: Notes < Active Windows < Commits < Tasks
        assert notes_pos < windows_pos < commits_pos < tasks_pos

        # Verify both window entries are present
        assert content.count("::: window") == 2
        assert "Terminal" in content
        assert "Safari" in content
