"""Tests for the query API for dynamic views."""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session
from backend.codex.main import app
from codex.db.models import FileMetadata, Notebook, Tag, FileTag
from codex.api.routes.query import (
    parse_sort_field,
    apply_path_filter,
    group_files,
    file_to_dict,
)

client = TestClient(app)


class TestHelperFunctions:
    """Test helper functions used by query API."""

    def test_parse_sort_field_asc(self):
        """Test parsing ascending sort field."""
        field, is_desc = parse_sort_field("created_at asc")
        assert field == "created_at"
        assert is_desc is False

    def test_parse_sort_field_desc(self):
        """Test parsing descending sort field."""
        field, is_desc = parse_sort_field("created_at desc")
        assert field == "created_at"
        assert is_desc is True

    def test_parse_sort_field_default(self):
        """Test parsing sort field without direction (defaults to asc)."""
        field, is_desc = parse_sort_field("title")
        assert field == "title"
        assert is_desc is False

    def test_parse_sort_field_case_insensitive(self):
        """Test parsing sort field with case-insensitive direction."""
        field, is_desc = parse_sort_field("title DESC")
        assert field == "title"
        assert is_desc is True

        field, is_desc = parse_sort_field("title ASC")
        assert field == "title"
        assert is_desc is False

    def test_apply_path_filter_exact_match(self):
        """Test path filter with exact match."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="docs/file1.md",
                filename="file1.md",
                file_type="md",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="src/file2.py",
                filename="file2.py",
                file_type="py",
                size=200,
                hash="def456",
            ),
        ]

        filtered = apply_path_filter(files, ["docs/file1.md"])
        assert len(filtered) == 1
        assert filtered[0].path == "docs/file1.md"

    def test_apply_path_filter_glob_pattern(self):
        """Test path filter with glob pattern."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="docs/file1.md",
                filename="file1.md",
                file_type="md",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="docs/file2.md",
                filename="file2.md",
                file_type="md",
                size=150,
                hash="def456",
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="src/file3.py",
                filename="file3.py",
                file_type="py",
                size=200,
                hash="ghi789",
            ),
        ]

        filtered = apply_path_filter(files, ["docs/*.md"])
        assert len(filtered) == 2
        assert all(f.path.startswith("docs/") for f in filtered)

    def test_apply_path_filter_multiple_patterns(self):
        """Test path filter with multiple patterns."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="docs/file1.md",
                filename="file1.md",
                file_type="md",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="src/file2.py",
                filename="file2.py",
                file_type="py",
                size=200,
                hash="def456",
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="tests/test_file.py",
                filename="test_file.py",
                file_type="py",
                size=150,
                hash="ghi789",
            ),
        ]

        filtered = apply_path_filter(files, ["docs/*.md", "src/*.py"])
        assert len(filtered) == 2
        assert any(f.path == "docs/file1.md" for f in filtered)
        assert any(f.path == "src/file2.py" for f in filtered)

    def test_group_files_by_standard_field(self):
        """Test grouping files by standard field."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="file1.md",
                filename="file1.md",
                file_type="md",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="file2.py",
                filename="file2.py",
                file_type="py",
                size=200,
                hash="def456",
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="file3.md",
                filename="file3.md",
                file_type="md",
                size=150,
                hash="ghi789",
            ),
        ]

        groups = group_files(files, "file_type")
        assert "md" in groups
        assert "py" in groups
        assert len(groups["md"]) == 2
        assert len(groups["py"]) == 1

    def test_group_files_by_property(self):
        """Test grouping files by property."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="file1.md",
                filename="file1.md",
                file_type="md",
                size=100,
                hash="abc123",
                properties=json.dumps({"status": "todo"}),
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="file2.md",
                filename="file2.md",
                file_type="md",
                size=200,
                hash="def456",
                properties=json.dumps({"status": "done"}),
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="file3.md",
                filename="file3.md",
                file_type="md",
                size=150,
                hash="ghi789",
                properties=json.dumps({"status": "todo"}),
            ),
        ]

        groups = group_files(files, "properties.status")
        assert "todo" in groups
        assert "done" in groups
        assert len(groups["todo"]) == 2
        assert len(groups["done"]) == 1

    def test_group_files_undefined_property(self):
        """Test grouping files when property doesn't exist."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="file1.md",
                filename="file1.md",
                file_type="md",
                size=100,
                hash="abc123",
                properties=json.dumps({"status": "todo"}),
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="file2.md",
                filename="file2.md",
                file_type="md",
                size=200,
                hash="def456",
                properties=None,
            ),
        ]

        groups = group_files(files, "properties.status")
        assert "todo" in groups
        assert "undefined" in groups
        assert len(groups["undefined"]) == 1

    def test_file_to_dict(self):
        """Test converting FileMetadata to dictionary."""
        now = datetime.now()
        file = FileMetadata(
            id=1,
            notebook_id=1,
            path="test.md",
            filename="test.md",
            file_type="md",
            size=100,
            hash="abc123",
            title="Test File",
            description="Test description",
            properties=json.dumps({"status": "todo", "priority": "high"}),
            created_at=now,
            updated_at=now,
            file_modified_at=now,
        )

        result = file_to_dict(file)
        assert result["id"] == 1
        assert result["path"] == "test.md"
        assert result["title"] == "Test File"
        assert result["properties"]["status"] == "todo"
        assert result["properties"]["priority"] == "high"
        assert result["created_at"] == now.isoformat()

    def test_file_to_dict_no_properties(self):
        """Test converting FileMetadata without properties."""
        file = FileMetadata(
            id=1,
            notebook_id=1,
            path="test.md",
            filename="test.md",
            file_type="md",
            size=100,
            hash="abc123",
            properties=None,
        )

        result = file_to_dict(file)
        assert result["properties"] is None

    def test_file_to_dict_invalid_json_properties(self):
        """Test converting FileMetadata with invalid JSON properties."""
        file = FileMetadata(
            id=1,
            notebook_id=1,
            path="test.md",
            filename="test.md",
            file_type="md",
            size=100,
            hash="abc123",
            properties="invalid json",
        )

        result = file_to_dict(file)
        assert result["properties"] is None


class TestQueryAPI:
    """Test query API endpoint."""

    def test_query_api_requires_authentication(self):
        """Test that query API requires authentication."""
        response = client.post("/api/v1/query/?workspace_id=1", json={})
        assert response.status_code == 401

    def test_query_api_accepts_valid_query(self):
        """Test that query API accepts valid query structure."""
        # This test will need proper authentication setup
        # For now, just test that the endpoint exists and validates input
        response = client.post(
            "/api/v1/query/?workspace_id=1",
            json={
                "file_types": ["md"],
                "limit": 10,
                "offset": 0,
            },
        )
        # Expect 401 since we don't have auth, but shows endpoint exists
        assert response.status_code == 401

    def test_query_model_validation(self):
        """Test ViewQuery model validation."""
        from codex.api.routes.query import ViewQuery

        # Test valid query
        query = ViewQuery(
            notebook_ids=[1, 2],
            tags=["important"],
            file_types=["md", "txt"],
            properties={"status": "todo"},
            sort="created_at desc",
            limit=50,
        )

        assert query.notebook_ids == [1, 2]
        assert query.tags == ["important"]
        assert query.limit == 50

    def test_query_model_defaults(self):
        """Test ViewQuery model default values."""
        from codex.api.routes.query import ViewQuery

        query = ViewQuery()
        assert query.limit == 100
        assert query.offset == 0
        assert query.notebook_ids is None
        assert query.tags is None


class TestPropertyFilters:
    """Test property filter application."""

    def test_property_filters_import(self):
        """Test that property filter functions can be imported."""
        from codex.api.routes.query import (
            apply_property_filters_to_query,
            apply_property_exists_filter_to_query,
            apply_date_property_filter_to_query,
        )

        # Just test they're callable
        assert callable(apply_property_filters_to_query)
        assert callable(apply_property_exists_filter_to_query)
        assert callable(apply_date_property_filter_to_query)


class TestQueryResult:
    """Test QueryResult model."""

    def test_query_result_model(self):
        """Test QueryResult model structure."""
        from codex.api.routes.query import QueryResult

        result = QueryResult(
            files=[{"id": 1, "title": "Test"}],
            groups=None,
            total=1,
            limit=10,
            offset=0,
        )

        assert len(result.files) == 1
        assert result.total == 1
        assert result.groups is None

    def test_query_result_with_groups(self):
        """Test QueryResult with grouped data."""
        from codex.api.routes.query import QueryResult

        result = QueryResult(
            files=[],
            groups={"todo": [{"id": 1}], "done": [{"id": 2}]},
            total=2,
            limit=10,
            offset=0,
        )

        assert len(result.files) == 0
        assert result.groups is not None
        assert "todo" in result.groups
        assert "done" in result.groups
