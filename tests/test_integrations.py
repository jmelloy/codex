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


class TestIntegrationVariables:
    """Tests for integration variables (default values for plugins)."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a test workspace."""
        return Workspace.initialize(tmp_path, "Test Workspace")

    def test_set_and_get_variable(self, workspace):
        """Test setting and getting a variable."""
        variable = workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="base_url",
            value="https://api.example.com",
            description="Default API server",
        )

        assert variable["integration_type"] == "api_call"
        assert variable["name"] == "base_url"
        assert variable["value"] == "https://api.example.com"
        assert variable["description"] == "Default API server"
        assert variable["is_secret"] is False

        # Get the variable
        retrieved = workspace.db_manager.get_integration_variable("api_call", "base_url")
        assert retrieved["value"] == "https://api.example.com"

    def test_set_variable_with_dict_value(self, workspace):
        """Test setting a variable with a dictionary value."""
        headers = {"Authorization": "Bearer token", "X-Custom": "value"}
        variable = workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="headers",
            value=headers,
            is_secret=True,
        )

        assert variable["value"] == headers
        assert variable["is_secret"] is True

    def test_update_variable(self, workspace):
        """Test updating an existing variable."""
        # Create variable
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="base_url",
            value="https://old.example.com",
        )

        # Update variable
        variable = workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="base_url",
            value="https://new.example.com",
        )

        assert variable["value"] == "https://new.example.com"

        # Verify only one variable exists
        variables = workspace.db_manager.list_integration_variables("api_call")
        assert len(variables) == 1

    def test_list_variables(self, workspace):
        """Test listing variables for an integration type."""
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="base_url",
            value="https://api.example.com",
        )
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="headers",
            value={"Authorization": "Bearer token"},
        )
        workspace.db_manager.set_integration_variable(
            integration_type="database_query",
            name="connection_string",
            value="postgresql://localhost/db",
        )

        api_call_vars = workspace.db_manager.list_integration_variables("api_call")
        assert len(api_call_vars) == 2

        all_vars = workspace.db_manager.list_integration_variables()
        assert len(all_vars) == 3

    def test_get_integration_variables_as_dict(self, workspace):
        """Test getting variables as a dictionary for merging."""
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="base_url",
            value="https://api.example.com",
        )
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="headers",
            value={"Authorization": "Bearer token"},
        )

        variables = workspace.db_manager.get_integration_variables("api_call")
        assert variables == {
            "base_url": "https://api.example.com",
            "headers": {"Authorization": "Bearer token"},
        }

    def test_delete_variable(self, workspace):
        """Test deleting a variable."""
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="base_url",
            value="https://api.example.com",
        )

        success = workspace.db_manager.delete_integration_variable("api_call", "base_url")
        assert success is True

        # Verify deleted
        variable = workspace.db_manager.get_integration_variable("api_call", "base_url")
        assert variable is None

    def test_delete_nonexistent_variable(self, workspace):
        """Test deleting a variable that doesn't exist."""
        success = workspace.db_manager.delete_integration_variable("api_call", "nonexistent")
        assert success is False


class TestIntegrationDefaultVariables:
    """Tests for integration default variable merging."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a test workspace."""
        return Workspace.initialize(tmp_path, "Test Workspace")

    def test_api_call_merge_with_defaults(self, workspace):
        """Test API call integration merges inputs with defaults."""
        # Set default variables
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="base_url",
            value="https://api.example.com",
        )
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="headers",
            value={"Authorization": "Bearer token"},
        )

        integration = APICallIntegration(workspace)

        # Entry only provides relative URL
        inputs = {"url": "/users"}
        merged = integration.merge_inputs_with_defaults(inputs)

        assert merged["base_url"] == "https://api.example.com"
        assert merged["url"] == "/users"
        assert merged["headers"] == {"Authorization": "Bearer token"}

    def test_api_call_merge_header_override(self, workspace):
        """Test that entry headers merge with default headers."""
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="headers",
            value={"Authorization": "Bearer token", "X-Default": "value"},
        )

        integration = APICallIntegration(workspace)

        # Entry provides additional header
        inputs = {"url": "https://example.com", "headers": {"X-Custom": "custom"}}
        merged = integration.merge_inputs_with_defaults(inputs)

        # Headers should be merged
        assert merged["headers"]["Authorization"] == "Bearer token"
        assert merged["headers"]["X-Default"] == "value"
        assert merged["headers"]["X-Custom"] == "custom"

    def test_api_call_input_overrides_default(self, workspace):
        """Test that entry inputs override defaults."""
        workspace.db_manager.set_integration_variable(
            integration_type="api_call",
            name="method",
            value="GET",
        )

        integration = APICallIntegration(workspace)

        # Entry overrides default method
        inputs = {"url": "https://example.com", "method": "POST"}
        merged = integration.merge_inputs_with_defaults(inputs)

        assert merged["method"] == "POST"

    def test_database_query_merge_with_defaults(self, workspace):
        """Test database query integration merges inputs with defaults."""
        workspace.db_manager.set_integration_variable(
            integration_type="database_query",
            name="connection_string",
            value="sqlite:///:memory:",
        )
        workspace.db_manager.set_integration_variable(
            integration_type="database_query",
            name="max_rows",
            value=100,
        )

        integration = DatabaseQueryIntegration(workspace)

        # Entry only provides query
        inputs = {"query": "SELECT 1"}
        merged = integration.merge_inputs_with_defaults(inputs)

        assert merged["connection_string"] == "sqlite:///:memory:"
        assert merged["query"] == "SELECT 1"
        assert merged["max_rows"] == 100

    def test_database_query_validate_with_defaults(self, workspace):
        """Test database query validation uses merged inputs."""
        workspace.db_manager.set_integration_variable(
            integration_type="database_query",
            name="connection_string",
            value="sqlite:///:memory:",
        )

        integration = DatabaseQueryIntegration(workspace)

        # Entry only provides query, connection_string comes from defaults
        inputs = {"query": "SELECT 1"}
        assert integration.validate_inputs(inputs) is True

    def test_graphql_merge_with_defaults(self, workspace):
        """Test GraphQL integration merges inputs with defaults."""
        workspace.db_manager.set_integration_variable(
            integration_type="graphql",
            name="url",
            value="https://api.example.com/graphql",
        )
        workspace.db_manager.set_integration_variable(
            integration_type="graphql",
            name="headers",
            value={"Authorization": "Bearer token"},
        )

        integration = GraphQLIntegration(workspace)

        # Entry only provides query
        inputs = {"query": "{ users { id } }"}
        merged = integration.merge_inputs_with_defaults(inputs)

        assert merged["url"] == "https://api.example.com/graphql"
        assert merged["query"] == "{ users { id } }"
        assert merged["headers"] == {"Authorization": "Bearer token"}

    @pytest.mark.asyncio
    async def test_database_query_execute_with_defaults(self, workspace):
        """Test executing database query with connection string from defaults."""
        workspace.db_manager.set_integration_variable(
            integration_type="database_query",
            name="connection_string",
            value="sqlite:///:memory:",
        )

        integration = DatabaseQueryIntegration(workspace)

        # Entry only provides query, connection_string comes from defaults
        inputs = {"query": "SELECT 1 as value"}
        result = await integration.execute(inputs)

        assert "outputs" in result
        assert result["outputs"]["row_count"] == 1
        assert result["outputs"]["results"][0]["value"] == 1

    @pytest.mark.asyncio
    async def test_entry_with_default_connection_string(self, workspace):
        """Test creating and executing entry with default connection string."""
        # Set default connection string
        workspace.db_manager.set_integration_variable(
            integration_type="database_query",
            name="connection_string",
            value="sqlite:///:memory:",
        )

        nb = workspace.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        # Create entry without connection_string - it should use the default
        entry = page.create_entry(
            entry_type="database_query",
            title="Test Query",
            inputs={"query": "SELECT 1 as value"},
        )

        # Execute the entry
        await entry.execute()

        assert entry.status == "completed"
        assert entry.outputs["row_count"] == 1
