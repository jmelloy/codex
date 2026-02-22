"""Tests for the query API for dynamic views."""

import json
from datetime import datetime

from codex.api.routes.query import (
    apply_path_filter,
    file_to_dict,
    group_files,
    parse_sort_field,
)
from codex.db.models import FileMetadata


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
                content_type="md",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="src/file2.py",
                filename="file2.py",
                content_type="py",
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
                content_type="md",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="docs/file2.md",
                filename="file2.md",
                content_type="md",
                size=150,
                hash="def456",
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="src/file3.py",
                filename="file3.py",
                content_type="py",
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
                content_type="md",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="src/file2.py",
                filename="file2.py",
                content_type="py",
                size=200,
                hash="def456",
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="tests/test_file.py",
                filename="test_file.py",
                content_type="py",
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
                content_type="text/markdown",
                size=100,
                hash="abc123",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="file2.py",
                filename="file2.py",
                content_type="text/x-python",
                size=200,
                hash="def456",
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="file3.md",
                filename="file3.md",
                content_type="text/markdown",
                size=150,
                hash="ghi789",
            ),
        ]

        groups = group_files(files, "content_type")
        assert "text/markdown" in groups
        assert "text/x-python" in groups
        assert len(groups["text/markdown"]) == 2
        assert len(groups["text/x-python"]) == 1

    def test_group_files_by_property(self):
        """Test grouping files by property."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="file1.md",
                filename="file1.md",
                content_type="md",
                size=100,
                hash="abc123",
                properties=json.dumps({"status": "todo"}),
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="file2.md",
                filename="file2.md",
                content_type="md",
                size=200,
                hash="def456",
                properties=json.dumps({"status": "done"}),
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="file3.md",
                filename="file3.md",
                content_type="md",
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
                content_type="md",
                size=100,
                hash="abc123",
                properties=json.dumps({"status": "todo"}),
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="file2.md",
                filename="file2.md",
                content_type="md",
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
            content_type="md",
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
            content_type="md",
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
            content_type="md",
            size=100,
            hash="abc123",
            properties="invalid json",
        )

        result = file_to_dict(file)
        assert result["properties"] is None


class TestQueryAPI:
    """Test query API endpoint."""

    def test_query_api_requires_authentication(self, test_client):
        """Test that query API requires authentication."""
        response = test_client.post("/api/v1/query/?workspace_id=1", json={})
        assert response.status_code == 401

    def test_query_api_accepts_valid_query(self, test_client):
        """Test that query API accepts valid query structure."""
        # This test will need proper authentication setup
        # For now, just test that the endpoint exists and validates input
        response = test_client.post(
            "/api/v1/query/?workspace_id=1",
            json={
                "file_types": ["md"],
                "limit": 10,
                "offset": 0,
            },
        )
        # Expect 401 since we don't have auth, but shows endpoint exists
        assert response.status_code == 401

    def test_query_api_nonexistent_workspace(self, test_client, auth_headers):
        """Test query API with nonexistent workspace returns 404."""
        headers = auth_headers[0]
        response = test_client.post(
            "/api/v1/query/?workspace_id=99999",
            json={"limit": 10},
            headers=headers,
        )
        assert response.status_code == 404

    def test_query_api_returns_files(self, test_client, auth_headers, workspace_and_notebook):
        """Test query API returns files from a workspace."""
        headers = auth_headers[0]
        workspace, notebook = workspace_and_notebook

        # Create some files first
        for i in range(3):
            test_client.post(
                f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
                json={"path": f"query_test_{i}.md", "content": f"# Query Test {i}"},
                headers=headers,
            )

        response = test_client.post(
            f"/api/v1/query/?workspace_id={workspace['id']}",
            json={"limit": 10},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_query_api_with_content_type_filter(self, test_client, auth_headers, workspace_and_notebook):
        """Test query API with content_type filter."""
        headers = auth_headers[0]
        workspace, notebook = workspace_and_notebook

        # Create files
        test_client.post(
            f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
            json={"path": "ct_test.md", "content": "# Markdown"},
            headers=headers,
        )

        response = test_client.post(
            f"/api/v1/query/?workspace_id={workspace['id']}",
            json={"content_types": ["text/markdown"], "limit": 10},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(f["content_type"] == "text/markdown" for f in data["files"])

    def test_query_api_pagination(self, test_client, auth_headers, workspace_and_notebook):
        """Test query API pagination with limit and offset."""
        headers = auth_headers[0]
        workspace, notebook = workspace_and_notebook

        # Create 5 files
        for i in range(5):
            test_client.post(
                f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/",
                json={"path": f"pag_test_{i}.md", "content": f"Content {i}"},
                headers=headers,
            )

        # Get first page
        resp1 = test_client.post(
            f"/api/v1/query/?workspace_id={workspace['id']}",
            json={"limit": 2, "offset": 0},
            headers=headers,
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert len(data1["files"]) == 2
        assert data1["total"] >= 5

        # Get second page
        resp2 = test_client.post(
            f"/api/v1/query/?workspace_id={workspace['id']}",
            json={"limit": 2, "offset": 2},
            headers=headers,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["files"]) == 2
        # Verify different files
        ids1 = {f["id"] for f in data1["files"]}
        ids2 = {f["id"] for f in data2["files"]}
        assert ids1.isdisjoint(ids2)

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
            apply_date_property_filter_to_query,
            apply_property_exists_filter_to_query,
            apply_property_filters_to_query,
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


class TestDynamicViewsWithTagsFilters:
    """Test dynamic views with tags and file_types filters."""

    def test_view_query_with_tags_filter(self):
        """Test ViewQuery with tags filter (AND logic)."""
        from codex.api.routes.query import ViewQuery

        query = ViewQuery(
            tags=["task", "urgent"],
            limit=50,
        )

        assert query.tags == ["task", "urgent"]
        assert query.tags_any is None

    def test_view_query_with_tags_any_filter(self):
        """Test ViewQuery with tags_any filter (OR logic)."""
        from codex.api.routes.query import ViewQuery

        query = ViewQuery(
            tags_any=["task", "note", "project"],
            limit=50,
        )

        assert query.tags_any == ["task", "note", "project"]
        assert query.tags is None

    def test_view_query_with_file_types_filter(self):
        """Test ViewQuery with file_types filter."""
        from codex.api.routes.query import ViewQuery

        query = ViewQuery(
            file_types=["todo", "note"],
            limit=50,
        )

        assert query.file_types == ["todo", "note"]

    def test_view_query_combined_tags_and_file_types(self):
        """Test ViewQuery with combined tags and file_types filters."""
        from codex.api.routes.query import ViewQuery

        query = ViewQuery(
            tags=["important"],
            file_types=["todo"],
            properties={"status": "in-progress"},
            limit=25,
        )

        assert query.tags == ["important"]
        assert query.file_types == ["todo"]
        assert query.properties == {"status": "in-progress"}
        assert query.limit == 25

    def test_file_to_dict_includes_file_type(self):
        """Test that file_to_dict includes file_type field."""
        now = datetime.now()
        file = FileMetadata(
            id=1,
            notebook_id=1,
            path="task.md",
            filename="task.md",
            content_type="text/markdown",
            size=100,
            hash="abc123",
            title="My Task",
            description="A task item",
            file_type="todo",
            properties=json.dumps({"status": "todo", "priority": "high"}),
            created_at=now,
            updated_at=now,
            file_modified_at=now,
        )

        result = file_to_dict(file)
        assert result["file_type"] == "todo"
        assert result["title"] == "My Task"
        assert result["properties"]["status"] == "todo"

    def test_group_files_by_file_type(self):
        """Test grouping files by file_type field."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="task1.md",
                filename="task1.md",
                content_type="text/markdown",
                size=100,
                hash="abc123",
                file_type="todo",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="note1.md",
                filename="note1.md",
                content_type="text/markdown",
                size=200,
                hash="def456",
                file_type="note",
            ),
            FileMetadata(
                id=3,
                notebook_id=1,
                path="task2.md",
                filename="task2.md",
                content_type="text/markdown",
                size=150,
                hash="ghi789",
                file_type="todo",
            ),
        ]

        groups = group_files(files, "file_type")
        assert "todo" in groups
        assert "note" in groups
        assert len(groups["todo"]) == 2
        assert len(groups["note"]) == 1

    def test_group_files_by_file_type_undefined(self):
        """Test grouping files when file_type is None."""
        files = [
            FileMetadata(
                id=1,
                notebook_id=1,
                path="task1.md",
                filename="task1.md",
                content_type="text/markdown",
                size=100,
                hash="abc123",
                file_type="todo",
            ),
            FileMetadata(
                id=2,
                notebook_id=1,
                path="file.md",
                filename="file.md",
                content_type="text/markdown",
                size=200,
                hash="def456",
                file_type=None,
            ),
        ]

        groups = group_files(files, "file_type")
        assert "todo" in groups
        assert "None" in groups or "undefined" in groups  # None becomes string "None"

    def test_view_query_for_kanban_view(self):
        """Test ViewQuery configuration for a kanban view."""
        from codex.api.routes.query import ViewQuery

        # Simulates a kanban board query that filters by file_type
        query = ViewQuery(
            file_types=["todo"],
            properties_exists=["status"],
            sort="properties.priority desc",
            limit=100,
        )

        assert query.file_types == ["todo"]
        assert query.properties_exists == ["status"]
        assert query.sort == "properties.priority desc"

    def test_view_query_for_task_list_view(self):
        """Test ViewQuery configuration for a task list view."""
        from codex.api.routes.query import ViewQuery

        # Simulates a task list query
        query = ViewQuery(
            file_types=["todo"],
            properties={"status": ["todo", "in-progress"]},
            sort="created_at desc",
            limit=50,
        )

        assert query.file_types == ["todo"]
        assert query.properties == {"status": ["todo", "in-progress"]}

    def test_view_query_for_gallery_with_pagination(self):
        """Test ViewQuery configuration for gallery view with pagination."""
        from codex.api.routes.query import ViewQuery

        # Simulates a gallery query with pagination
        query = ViewQuery(
            content_types=["image/jpeg", "image/png", "image/gif", "image/webp"],
            sort="file_modified_at desc",
            limit=24,
            offset=48,  # Page 3 with 24 items per page
        )

        assert query.content_types == ["image/jpeg", "image/png", "image/gif", "image/webp"]
        assert query.limit == 24
        assert query.offset == 48

    def test_view_query_combined_content_types_and_tags(self):
        """Test ViewQuery with both content_types and tags for filtered gallery."""
        from codex.api.routes.query import ViewQuery

        # Simulates a gallery showing only tagged images
        query = ViewQuery(
            content_types=["image/jpeg", "image/png"],
            tags_any=["favorites", "portfolio"],
            limit=20,
        )

        assert query.content_types == ["image/jpeg", "image/png"]
        assert query.tags_any == ["favorites", "portfolio"]


class TestFileMetadataWithFileType:
    """Test FileMetadata model with file_type field."""

    def test_file_metadata_with_file_type(self):
        """Test creating FileMetadata with file_type."""
        file = FileMetadata(
            id=1,
            notebook_id=1,
            path="task.md",
            filename="task.md",
            content_type="text/markdown",
            size=100,
            hash="abc123",
            file_type="todo",
        )

        assert file.file_type == "todo"

    def test_file_metadata_file_type_none(self):
        """Test FileMetadata with no file_type."""
        file = FileMetadata(
            id=1,
            notebook_id=1,
            path="random.md",
            filename="random.md",
            content_type="text/markdown",
            size=100,
            hash="abc123",
        )

        assert file.file_type is None

    def test_file_to_dict_file_type_none(self):
        """Test file_to_dict when file_type is None."""
        file = FileMetadata(
            id=1,
            notebook_id=1,
            path="test.md",
            filename="test.md",
            content_type="text/markdown",
            size=100,
            hash="abc123",
            file_type=None,
        )

        result = file_to_dict(file)
        assert result["file_type"] is None
