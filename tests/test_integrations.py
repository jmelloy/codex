"""Tests for database query and GraphQL integrations."""

import json

import pytest

from codex.core.workspace import Workspace
from codex.integrations import IntegrationRegistry
from codex.integrations.api_call import APICallIntegration
from codex.integrations.database_query import DatabaseQueryIntegration
from codex.integrations.graphql import GraphQLIntegration


class TestIntegrationRegistry:
    """Tests for integration registry."""

    def test_database_query_registered(self):
        """Test database_query integration is registered."""
        assert IntegrationRegistry.has_integration("database_query")
        cls = IntegrationRegistry.get("database_query")
        assert cls == DatabaseQueryIntegration

    def test_graphql_registered(self):
        """Test graphql integration is registered."""
        assert IntegrationRegistry.has_integration("graphql")
        cls = IntegrationRegistry.get("graphql")
        assert cls == GraphQLIntegration

    def test_api_call_registered(self):
        """Test api_call integration is registered."""
        assert IntegrationRegistry.has_integration("api_call")
        cls = IntegrationRegistry.get("api_call")
        assert cls == APICallIntegration

    def test_list_integrations(self):
        """Test listing all integrations."""
        integrations = IntegrationRegistry.list_integrations()
        assert "database_query" in integrations
        assert "graphql" in integrations
        assert "custom" in integrations
        assert "api_call" in integrations


class TestDatabaseQueryIntegration:
    """Tests for DatabaseQueryIntegration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a test workspace."""
        return Workspace.initialize(tmp_path, "Test Workspace")

    @pytest.fixture
    def integration(self, workspace):
        """Create integration instance."""
        return DatabaseQueryIntegration(workspace)

    def test_validate_inputs_valid(self, integration):
        """Test input validation with valid inputs."""
        inputs = {
            "connection_string": "sqlite:///:memory:",
            "query": "SELECT 1",
        }
        assert integration.validate_inputs(inputs) is True

    def test_validate_inputs_missing_connection_string(self, integration):
        """Test input validation with missing connection string."""
        inputs = {
            "query": "SELECT 1",
        }
        assert integration.validate_inputs(inputs) is False

    def test_validate_inputs_missing_query(self, integration):
        """Test input validation with missing query."""
        inputs = {
            "connection_string": "sqlite:///:memory:",
        }
        assert integration.validate_inputs(inputs) is False

    @pytest.mark.asyncio
    async def test_execute_sqlite_select(self, integration):
        """Test executing a SELECT query on SQLite."""
        inputs = {
            "connection_string": "sqlite:///:memory:",
            "query": "SELECT 1 as value, 'hello' as text",
        }

        result = await integration.execute(inputs)

        assert "outputs" in result
        assert "artifacts" in result

        outputs = result["outputs"]
        assert outputs["row_count"] == 1
        assert "value" in outputs["columns"]
        assert "text" in outputs["columns"]
        assert len(outputs["results"]) == 1
        assert outputs["results"][0]["value"] == 1
        assert outputs["results"][0]["text"] == "hello"
        assert "duration_seconds" in outputs

        # Check artifact
        assert len(result["artifacts"]) == 1
        artifact = result["artifacts"][0]
        assert artifact["type"] == "application/json"
        artifact_data = json.loads(artifact["data"].decode("utf-8"))
        assert artifact_data["row_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_sqlite_with_parameters(self, integration, tmp_path):
        """Test executing a parameterized query on SQLite."""
        # Create a test database with a table
        db_path = tmp_path / "test.db"
        inputs_create = {
            "connection_string": f"sqlite:///{db_path}",
            "query": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)",
        }
        await integration.execute(inputs_create)

        # Insert data
        inputs_insert = {
            "connection_string": f"sqlite:///{db_path}",
            "query": "INSERT INTO users (name, age) VALUES (:name, :age)",
            "parameters": {"name": "Alice", "age": 30},
        }
        result = await integration.execute(inputs_insert)
        assert result["outputs"]["affected_rows"] == 1

        # Query with parameters
        inputs_select = {
            "connection_string": f"sqlite:///{db_path}",
            "query": "SELECT * FROM users WHERE age > :min_age",
            "parameters": {"min_age": 25},
        }
        result = await integration.execute(inputs_select)

        outputs = result["outputs"]
        assert outputs["row_count"] == 1
        assert outputs["results"][0]["name"] == "Alice"
        assert outputs["results"][0]["age"] == 30

    @pytest.mark.asyncio
    async def test_execute_max_rows_limit(self, integration, tmp_path):
        """Test that max_rows limits the results."""
        db_path = tmp_path / "test.db"

        # Create table and insert multiple rows
        inputs_create = {
            "connection_string": f"sqlite:///{db_path}",
            "query": "CREATE TABLE numbers (n INTEGER)",
        }
        await integration.execute(inputs_create)

        for i in range(10):
            inputs_insert = {
                "connection_string": f"sqlite:///{db_path}",
                "query": f"INSERT INTO numbers (n) VALUES ({i})",
            }
            await integration.execute(inputs_insert)

        # Query with max_rows limit
        inputs_select = {
            "connection_string": f"sqlite:///{db_path}",
            "query": "SELECT * FROM numbers",
            "max_rows": 5,
        }
        result = await integration.execute(inputs_select)

        outputs = result["outputs"]
        assert outputs["row_count"] == 5
        assert len(outputs["results"]) == 5

    @pytest.mark.asyncio
    async def test_execute_invalid_query(self, integration):
        """Test error handling for invalid query."""
        inputs = {
            "connection_string": "sqlite:///:memory:",
            "query": "INVALID SQL QUERY",
        }

        result = await integration.execute(inputs)

        outputs = result["outputs"]
        assert "error" in outputs
        assert "duration_seconds" in outputs

    @pytest.mark.asyncio
    async def test_entry_with_database_query(self, workspace):
        """Test creating an entry with database_query type."""
        nb = workspace.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        entry = page.create_entry(
            entry_type="database_query",
            title="Test Database Query",
            inputs={
                "connection_string": "sqlite:///:memory:",
                "query": "SELECT 1 as value",
            },
        )

        assert entry.entry_type == "database_query"
        assert entry.inputs["connection_string"] == "sqlite:///:memory:"

        # Execute the entry
        await entry.execute()

        assert entry.status == "completed"
        assert entry.outputs["row_count"] == 1


class TestGraphQLIntegration:
    """Tests for GraphQLIntegration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a test workspace."""
        return Workspace.initialize(tmp_path, "Test Workspace")

    @pytest.fixture
    def integration(self, workspace):
        """Create integration instance."""
        return GraphQLIntegration(workspace)

    def test_validate_inputs_valid(self, integration):
        """Test input validation with valid inputs."""
        inputs = {
            "url": "https://api.example.com/graphql",
            "query": "query { users { id } }",
        }
        assert integration.validate_inputs(inputs) is True

    def test_validate_inputs_missing_url(self, integration):
        """Test input validation with missing URL."""
        inputs = {
            "query": "query { users { id } }",
        }
        assert integration.validate_inputs(inputs) is False

    def test_validate_inputs_missing_query(self, integration):
        """Test input validation with missing query."""
        inputs = {
            "url": "https://api.example.com/graphql",
        }
        assert integration.validate_inputs(inputs) is False

    def test_validate_inputs_with_variables(self, integration):
        """Test input validation with variables."""
        inputs = {
            "url": "https://api.example.com/graphql",
            "query": "query GetUser($id: ID!) { user(id: $id) { name } }",
            "variables": {"id": "123"},
        }
        assert integration.validate_inputs(inputs) is True

    @pytest.mark.asyncio
    async def test_execute_connection_error(self, integration):
        """Test error handling for connection errors."""
        inputs = {
            "url": "http://localhost:99999/graphql",
            "query": "query { test }",
        }

        result = await integration.execute(inputs)

        outputs = result["outputs"]
        assert "error" in outputs
        assert outputs["has_errors"] is True
        assert "duration_seconds" in outputs

    @pytest.mark.asyncio
    async def test_entry_with_graphql(self, workspace):
        """Test creating an entry with graphql type."""
        nb = workspace.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        entry = page.create_entry(
            entry_type="graphql",
            title="Test GraphQL Query",
            inputs={
                "url": "https://api.example.com/graphql",
                "query": "query { users { id name } }",
                "variables": {"limit": 10},
            },
        )

        assert entry.entry_type == "graphql"
        assert entry.inputs["url"] == "https://api.example.com/graphql"
        assert entry.inputs["variables"] == {"limit": 10}


class TestAPICallIntegration:
    """Tests for APICallIntegration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a test workspace."""
        return Workspace.initialize(tmp_path, "Test Workspace")

    @pytest.fixture
    def integration(self, workspace):
        """Create integration instance."""
        return APICallIntegration(workspace)

    def test_validate_inputs_valid(self, integration):
        """Test input validation with valid inputs."""
        inputs = {
            "url": "https://api.example.com/endpoint",
            "method": "GET",
        }
        assert integration.validate_inputs(inputs) is True

    def test_validate_inputs_valid_with_body(self, integration):
        """Test input validation with valid inputs including body."""
        inputs = {
            "url": "https://api.example.com/endpoint",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": {"key": "value"},
        }
        assert integration.validate_inputs(inputs) is True

    def test_validate_inputs_missing_url(self, integration):
        """Test input validation with missing URL."""
        inputs = {
            "method": "GET",
        }
        assert integration.validate_inputs(inputs) is False

    def test_validate_inputs_minimal(self, integration):
        """Test input validation with only URL."""
        inputs = {
            "url": "https://api.example.com/endpoint",
        }
        assert integration.validate_inputs(inputs) is True

    @pytest.mark.asyncio
    async def test_execute_connection_error(self, integration):
        """Test error handling for connection errors."""
        inputs = {
            "url": "http://localhost:99999/api",
            "method": "GET",
        }

        result = await integration.execute(inputs)

        outputs = result["outputs"]
        assert "error" in outputs
        assert "duration_seconds" in outputs

    @pytest.mark.asyncio
    async def test_entry_with_api_call(self, workspace):
        """Test creating an entry with api_call type."""
        nb = workspace.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        entry = page.create_entry(
            entry_type="api_call",
            title="Test API Call",
            inputs={
                "url": "https://api.example.com/endpoint",
                "method": "POST",
                "headers": {"Authorization": "Bearer token"},
                "body": {"key": "value"},
            },
        )

        assert entry.entry_type == "api_call"
        assert entry.inputs["url"] == "https://api.example.com/endpoint"
        assert entry.inputs["method"] == "POST"
        assert entry.inputs["headers"] == {"Authorization": "Bearer token"}
