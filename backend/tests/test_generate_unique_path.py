"""Unit tests for the generate_unique_path helper."""

import os
from pathlib import Path

from codex.api.routes.files import generate_unique_path


def test_returns_path_unchanged_when_no_conflict(tmp_path):
    """When the file does not exist, the original path is returned."""
    p = tmp_path / "notes.md"
    assert generate_unique_path(p) == p


def test_appends_suffix_1_on_first_conflict(tmp_path):
    """First duplicate gets a -1 suffix."""
    original = tmp_path / "notes.md"
    original.touch()

    result = generate_unique_path(original)
    assert result == tmp_path / "notes-1.md"


def test_increments_suffix_on_multiple_conflicts(tmp_path):
    """Successive duplicates increment the numeric suffix."""
    original = tmp_path / "notes.md"
    original.touch()
    (tmp_path / "notes-1.md").touch()
    (tmp_path / "notes-2.md").touch()

    result = generate_unique_path(original)
    assert result == tmp_path / "notes-3.md"


def test_works_with_no_extension(tmp_path):
    """Files without an extension still get a suffix."""
    original = tmp_path / "README"
    original.touch()

    result = generate_unique_path(original)
    assert result == tmp_path / "README-1"


def test_works_with_compound_extension(tmp_path):
    """Only the last extension is preserved after the suffix."""
    original = tmp_path / "archive.tar.gz"
    original.touch()

    result = generate_unique_path(original)
    # Path.stem gives 'archive.tar', Path.suffix gives '.gz'
    assert result == tmp_path / "archive.tar-1.gz"


def test_works_in_subdirectory(tmp_path):
    """Suffix is appended within the correct subdirectory."""
    subdir = tmp_path / "sub"
    subdir.mkdir()
    original = subdir / "page.md"
    original.touch()

    result = generate_unique_path(original)
    assert result == subdir / "page-1.md"
    assert result.parent == subdir
