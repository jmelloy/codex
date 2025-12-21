"""Tests for database query and GraphQL integrations."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.workspace import Workspace
from integrations import IntegrationRegistry
from integrations.api_call import APICallIntegration
from integrations.comfyui import ComfyUIClient, ComfyUIIntegration
from integrations.database_query import DatabaseQueryIntegration
from integrations.graphql import GraphQLIntegration


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

    def test_comfyui_registered(self):
        """Test comfyui integration is registered."""
        assert IntegrationRegistry.has_integration("comfyui")
        cls = IntegrationRegistry.get("comfyui")
        assert cls == ComfyUIIntegration

    def test_list_integrations(self):
        """Test listing all integrations."""
        integrations = IntegrationRegistry.list_integrations()
        assert "database_query" in integrations
        assert "graphql" in integrations
        assert "custom" in integrations
        assert "api_call" in integrations
        assert "comfyui" in integrations


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
        retrieved = workspace.db_manager.get_integration_variable(
            "api_call", "base_url"
        )
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

        success = workspace.db_manager.delete_integration_variable(
            "api_call", "base_url"
        )
        assert success is True

        # Verify deleted
        variable = workspace.db_manager.get_integration_variable("api_call", "base_url")
        assert variable is None

    def test_delete_nonexistent_variable(self, workspace):
        """Test deleting a variable that doesn't exist."""
        success = workspace.db_manager.delete_integration_variable(
            "api_call", "nonexistent"
        )
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


class TestComfyUIIntegration:
    """Tests for ComfyUIIntegration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a test workspace."""
        return Workspace.initialize(tmp_path, "Test Workspace")

    @pytest.fixture
    def integration(self, workspace):
        """Create integration instance."""
        return ComfyUIIntegration(workspace)

    def test_validate_inputs_valid(self, integration):
        """Test input validation with valid inputs."""
        inputs = {
            "workflow": {"1": {"class_type": "CheckpointLoaderSimple"}},
        }
        assert integration.validate_inputs(inputs) is True

    def test_validate_inputs_missing_workflow(self, integration):
        """Test input validation with missing workflow."""
        inputs = {}
        assert integration.validate_inputs(inputs) is False

    def test_validate_inputs_invalid_workflow_type(self, integration):
        """Test input validation with non-dict workflow."""
        inputs = {
            "workflow": "not a dict",
        }
        assert integration.validate_inputs(inputs) is False

    def test_validate_inputs_with_optional_params(self, integration):
        """Test input validation with optional parameters."""
        inputs = {
            "workflow": {"1": {"class_type": "CheckpointLoaderSimple"}},
            "timeout": 600,
            "poll_interval": 2.0,
        }
        assert integration.validate_inputs(inputs) is True

    @pytest.mark.asyncio
    async def test_execute_successful_workflow(self, integration):
        """Test executing a workflow successfully."""
        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model.safetensors"},
            }
        }

        # Mock the ComfyUIClient
        with patch("integrations.comfyui.ComfyUIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock queue_prompt
            mock_client.queue_prompt = AsyncMock(return_value="test-prompt-123")

            # Mock wait_for_completion
            mock_client.wait_for_completion = AsyncMock(
                return_value={
                    "outputs": {
                        "9": {
                            "images": [
                                {
                                    "filename": "output_00001_.png",
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    }
                }
            )

            # Mock download_image
            mock_client.download_image = AsyncMock(return_value=b"fake-image-data")

            inputs = {"workflow": workflow}
            result = await integration.execute(inputs)

            assert "outputs" in result
            assert "artifacts" in result

            outputs = result["outputs"]
            assert outputs["prompt_id"] == "test-prompt-123"
            assert "execution_time" in outputs
            assert outputs["num_images"] == 1

            artifacts = result["artifacts"]
            assert len(artifacts) == 1
            assert artifacts[0]["type"] == "image/png"
            assert artifacts[0]["data"] == b"fake-image-data"
            assert artifacts[0]["metadata"]["filename"] == "output_00001_.png"
            assert artifacts[0]["metadata"]["node_id"] == "9"

    @pytest.mark.asyncio
    async def test_execute_with_multiple_images(self, integration):
        """Test executing workflow that generates multiple images."""
        workflow = {"1": {"class_type": "KSampler"}}

        with patch("integrations.comfyui.ComfyUIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.queue_prompt = AsyncMock(return_value="test-prompt-456")
            mock_client.wait_for_completion = AsyncMock(
                return_value={
                    "outputs": {
                        "9": {
                            "images": [
                                {"filename": "img1.png", "subfolder": ""},
                                {"filename": "img2.png", "subfolder": "batch"},
                            ]
                        },
                        "10": {
                            "images": [
                                {"filename": "img3.jpg", "subfolder": ""},
                            ]
                        },
                    }
                }
            )
            mock_client.download_image = AsyncMock(return_value=b"image-data")

            result = await integration.execute({"workflow": workflow})

            assert result["outputs"]["num_images"] == 3
            assert len(result["artifacts"]) == 3

            # Check MIME types
            assert result["artifacts"][0]["type"] == "image/png"
            assert result["artifacts"][1]["type"] == "image/png"
            assert result["artifacts"][2]["type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_execute_with_custom_server_url(self, integration):
        """Test executing with custom server URL."""
        workflow = {"1": {"class_type": "CheckpointLoaderSimple"}}

        with patch("integrations.comfyui.ComfyUIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.queue_prompt = AsyncMock(return_value="test-prompt-789")
            mock_client.wait_for_completion = AsyncMock(return_value={"outputs": {}})

            inputs = {
                "workflow": workflow,
                "server_url": "http://custom-server:8188",
            }
            await integration.execute(inputs)

            # Verify client was created with custom URL
            mock_client_class.assert_called_once_with("http://custom-server:8188")

    @pytest.mark.asyncio
    async def test_execute_timeout_error(self, integration):
        """Test handling of timeout errors."""
        workflow = {"1": {"class_type": "KSampler"}}

        with patch("integrations.comfyui.ComfyUIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.queue_prompt = AsyncMock(return_value="test-timeout")
            mock_client.wait_for_completion = AsyncMock(
                side_effect=TimeoutError("Workflow execution timed out")
            )

            result = await integration.execute({"workflow": workflow})

            assert "error" in result["outputs"]
            assert "timed out" in result["outputs"]["error"].lower()
            assert len(result["artifacts"]) == 0

    @pytest.mark.asyncio
    async def test_execute_connection_error(self, integration):
        """Test handling of connection errors."""
        workflow = {"1": {"class_type": "KSampler"}}

        with patch("integrations.comfyui.ComfyUIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.queue_prompt = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            result = await integration.execute({"workflow": workflow})

            assert "error" in result["outputs"]
            assert "Connection refused" in result["outputs"]["error"]

    @pytest.mark.asyncio
    async def test_entry_with_comfyui(self, workspace):
        """Test creating an entry with comfyui type."""
        nb = workspace.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        workflow = {
            "3": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
            }
        }

        entry = page.create_entry(
            entry_type="comfyui",
            title="Test ComfyUI Workflow",
            inputs={
                "workflow": workflow,
                "timeout": 600,
            },
        )

        assert entry.entry_type == "comfyui"
        assert entry.inputs["workflow"] == workflow
        assert entry.inputs["timeout"] == 600


class TestComfyUIClient:
    """Tests for ComfyUIClient."""

    @pytest.mark.asyncio
    async def test_queue_prompt(self):
        """Test queuing a prompt."""
        client = ComfyUIClient("http://test-server:8188")
        workflow = {"1": {"class_type": "LoadImage"}}

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            mock_response = MagicMock()
            mock_response.json = AsyncMock(return_value={"prompt_id": "abc123"})
            mock_response.raise_for_status = MagicMock()

            mock_session.post.return_value.__aenter__.return_value = mock_response

            prompt_id = await client.queue_prompt(workflow)

            assert prompt_id == "abc123"
            mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history(self):
        """Test getting workflow history."""
        client = ComfyUIClient("http://test-server:8188")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            mock_response = MagicMock()
            mock_response.json = AsyncMock(return_value={"prompt-123": {"outputs": {}}})
            mock_response.raise_for_status = MagicMock()

            mock_session.get.return_value.__aenter__.return_value = mock_response

            history = await client.get_history("prompt-123")

            assert "outputs" in history
            assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_download_image(self):
        """Test downloading an image."""
        client = ComfyUIClient("http://test-server:8188")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            mock_response = MagicMock()
            mock_response.read = AsyncMock(return_value=b"image-bytes")
            mock_response.raise_for_status = MagicMock()

            mock_session.get.return_value.__aenter__.return_value = mock_response

            image_data = await client.download_image("test.png")

            assert image_data == b"image-bytes"


class TestComfyUIIntegrationVariables:
    """Tests for ComfyUI integration default variables."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a test workspace."""
        return Workspace.initialize(tmp_path, "Test Workspace")

    def test_comfyui_merge_with_defaults(self, workspace):
        """Test ComfyUI integration merges inputs with defaults."""
        # Set default server URL
        workspace.db_manager.set_integration_variable(
            integration_type="comfyui",
            name="server_url",
            value="http://custom-comfy:8188",
        )

        integration = ComfyUIIntegration(workspace)

        # Entry only provides workflow
        inputs = {"workflow": {"1": {"class_type": "KSampler"}}}
        merged = integration.merge_inputs_with_defaults(inputs)

        assert merged["server_url"] == "http://custom-comfy:8188"
        assert merged["workflow"] == {"1": {"class_type": "KSampler"}}

    def test_comfyui_input_overrides_default(self, workspace):
        """Test that entry inputs override defaults."""
        workspace.db_manager.set_integration_variable(
            integration_type="comfyui",
            name="server_url",
            value="http://default-server:8188",
        )

        integration = ComfyUIIntegration(workspace)

        # Entry overrides default server URL
        inputs = {
            "workflow": {"1": {"class_type": "KSampler"}},
            "server_url": "http://override-server:8188",
        }
        merged = integration.merge_inputs_with_defaults(inputs)

        assert merged["server_url"] == "http://override-server:8188"

    @pytest.mark.asyncio
    async def test_comfyui_validate_with_defaults(self, workspace):
        """Test ComfyUI validation works with defaults."""
        workspace.db_manager.set_integration_variable(
            integration_type="comfyui",
            name="server_url",
            value="http://default-server:8188",
        )

        integration = ComfyUIIntegration(workspace)

        # Entry only provides workflow
        inputs = {"workflow": {"1": {"class_type": "KSampler"}}}
        assert integration.validate_inputs(inputs) is True

    @pytest.mark.asyncio
    async def test_entry_with_default_server_url(self, workspace):
        """Test creating and executing entry with default server URL."""
        # Set default server URL
        workspace.db_manager.set_integration_variable(
            integration_type="comfyui",
            name="server_url",
            value="http://test-server:8188",
        )

        nb = workspace.create_notebook("Test Notebook")
        page = nb.create_page("Test Page")

        # Create entry without server_url - it should use the default
        entry = page.create_entry(
            entry_type="comfyui",
            title="Test Workflow",
            inputs={"workflow": {"1": {"class_type": "LoadImage"}}},
        )

        # Mock execution
        with patch("integrations.comfyui.ComfyUIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.queue_prompt = AsyncMock(return_value="test-prompt")
            mock_client.wait_for_completion = AsyncMock(return_value={"outputs": {}})

            await entry.execute()

            # Verify client was created with default URL
            mock_client_class.assert_called_once_with("http://test-server:8188")
            assert entry.status == "completed"
