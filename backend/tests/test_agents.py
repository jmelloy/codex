"""Tests for AI agent endpoints and core modules."""

import pytest


# ---------------------------------------------------------------------------
# Unit tests for ScopeGuard
# ---------------------------------------------------------------------------


class TestScopeGuard:
    """Tests for the ScopeGuard access control."""

    def _make_agent(self, **overrides):
        """Create a minimal agent-like object for testing."""
        from unittest.mock import MagicMock

        defaults = {
            "name": "test-agent",
            "can_read": True,
            "can_write": False,
            "can_create": False,
            "can_delete": False,
            "can_execute_code": False,
            "scope": {"notebooks": ["*"], "folders": ["*"], "file_types": ["*"]},
        }
        defaults.update(overrides)
        agent = MagicMock(**defaults)
        agent.scope = defaults["scope"]
        return agent

    def test_read_allowed_by_default(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        assert guard.check_path_access("notes/hello.md", "read") is True

    def test_write_denied_by_default(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        assert guard.check_path_access("notes/hello.md", "write") is False

    def test_write_allowed_when_granted(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent(can_write=True)
        guard = ScopeGuard(agent)
        assert guard.check_path_access("notes/hello.md", "write") is True

    def test_path_traversal_blocked(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        assert guard.check_path_access("../../etc/passwd", "read") is False

    def test_folder_restriction(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent(scope={"notebooks": ["*"], "folders": ["/experiments/*"], "file_types": ["*"]})
        guard = ScopeGuard(agent)
        assert guard.check_path_access("/experiments/trial1.md", "read") is True
        assert guard.check_path_access("/notes/private.md", "read") is False

    def test_file_type_restriction(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent(scope={"notebooks": ["*"], "folders": ["*"], "file_types": ["*.md", "*.txt"]})
        guard = ScopeGuard(agent)
        assert guard.check_path_access("hello.md", "read") is True
        assert guard.check_path_access("hello.py", "read") is False

    def test_notebook_access(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent(scope={"notebooks": ["lab-notebook"], "folders": ["*"], "file_types": ["*"]})
        guard = ScopeGuard(agent)
        assert guard.check_notebook_access("lab-notebook") is True
        assert guard.check_notebook_access("other-notebook") is False

    def test_notebook_wildcard_access(self):
        from codex.agents.scope import ScopeGuard

        agent = self._make_agent(scope={"notebooks": ["*"], "folders": ["*"], "file_types": ["*"]})
        guard = ScopeGuard(agent)
        assert guard.check_notebook_access("any-notebook") is True

    def test_validate_or_raise(self):
        from codex.agents.scope import ScopeGuard, ScopeViolation

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        # Read should pass
        guard.validate_or_raise("read", "hello.md")
        # Write should raise
        with pytest.raises(ScopeViolation):
            guard.validate_or_raise("write", "hello.md")


# ---------------------------------------------------------------------------
# Unit tests for ToolRouter
# ---------------------------------------------------------------------------


class TestToolRouter:
    """Tests for the ToolRouter tool definitions and execution."""

    def _make_agent(self, **overrides):
        from unittest.mock import MagicMock

        defaults = {
            "name": "test-agent",
            "can_read": True,
            "can_write": False,
            "can_create": False,
            "can_delete": False,
            "can_execute_code": False,
            "scope": {"notebooks": ["*"], "folders": ["*"], "file_types": ["*"]},
        }
        defaults.update(overrides)
        agent = MagicMock(**defaults)
        agent.scope = defaults["scope"]
        return agent

    def _make_session(self):
        from unittest.mock import MagicMock

        session = MagicMock()
        session.files_modified = []
        return session

    def test_read_only_tools(self):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), "/tmp/test")
        tools = router.get_tool_definitions()
        tool_names = {t.name for t in tools}
        assert "read_file" in tool_names
        assert "list_files" in tool_names
        assert "search_content" in tool_names
        assert "write_file" not in tool_names
        assert "create_file" not in tool_names
        assert "delete_file" not in tool_names

    def test_write_tools_when_granted(self):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        agent = self._make_agent(can_write=True, can_create=True, can_delete=True)
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), "/tmp/test")
        tools = router.get_tool_definitions()
        tool_names = {t.name for t in tools}
        assert "write_file" in tool_names
        assert "create_file" in tool_names
        assert "delete_file" in tool_names

    def test_litellm_format(self):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), "/tmp/test")
        litellm_tools = router.get_tool_definitions_for_litellm()
        assert len(litellm_tools) > 0
        for tool in litellm_tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "parameters" in tool["function"]

    @pytest.mark.asyncio
    async def test_read_file(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        # Create a test file
        test_file = tmp_path / "hello.md"
        test_file.write_text("# Hello World")

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), str(tmp_path))
        result = await router.execute_tool("read_file", {"path": "hello.md"}, confirmed=True)
        assert result["content"] == "# Hello World"
        assert result["path"] == "hello.md"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), str(tmp_path))
        result = await router.execute_tool("read_file", {"path": "missing.md"}, confirmed=True)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_files(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / ".hidden").write_text("hidden")

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), str(tmp_path))
        result = await router.execute_tool("list_files", {"path": "/"}, confirmed=True)
        names = [f["name"] for f in result["files"]]
        assert "a.md" in names
        assert "b.txt" in names
        assert ".hidden" not in names  # Hidden files excluded

    @pytest.mark.asyncio
    async def test_create_and_write_file(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        agent = self._make_agent(can_write=True, can_create=True)
        guard = ScopeGuard(agent)
        session = self._make_session()
        router = ToolRouter(guard, session, str(tmp_path))

        # Create a new file
        result = await router.execute_tool("create_file", {"path": "new.md", "content": "initial"}, confirmed=True)
        assert result["created"] is True
        assert (tmp_path / "new.md").read_text() == "initial"

        # Write/update the file
        result = await router.execute_tool("write_file", {"path": "new.md", "content": "updated"}, confirmed=True)
        assert result["written"] == 7
        assert (tmp_path / "new.md").read_text() == "updated"

    @pytest.mark.asyncio
    async def test_scope_violation_logged(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        (tmp_path / "hello.md").write_text("content")

        agent = self._make_agent()  # read-only
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), str(tmp_path))
        result = await router.execute_tool("write_file", {"path": "hello.md", "content": "hack"}, confirmed=True)
        # Should not find write_file tool (read-only agent)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_content(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        (tmp_path / "notes.md").write_text("The experiment yielded results.")
        (tmp_path / "other.md").write_text("Nothing here.")

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), str(tmp_path))
        result = await router.execute_tool("search_content", {"query": "experiment"}, confirmed=True)
        assert result["total"] >= 1
        paths = [r["path"] for r in result["results"]]
        assert "notes.md" in paths

    @pytest.mark.asyncio
    async def test_confirmation_required(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        agent = self._make_agent(can_create=True)
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), str(tmp_path))
        result = await router.execute_tool("create_file", {"path": "new.md"}, confirmed=False)
        assert result.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_path_escape_blocked(self, tmp_path):
        from codex.agents.scope import ScopeGuard
        from codex.agents.tools import ToolRouter

        agent = self._make_agent()
        guard = ScopeGuard(agent)
        router = ToolRouter(guard, self._make_session(), str(tmp_path))
        result = await router.execute_tool("read_file", {"path": "../../etc/passwd"}, confirmed=True)
        assert "error" in result or "scope_violation" in result


# ---------------------------------------------------------------------------
# Unit tests for LiteLLMProvider
# ---------------------------------------------------------------------------


class TestLiteLLMProvider:
    """Tests for the LiteLLM provider adapter."""

    def test_message_conversion(self):
        from codex.agents.provider import LiteLLMProvider, Message

        provider = LiteLLMProvider(model="gpt-4o", api_key="test")
        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi!", tool_calls=[{"id": "1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}]),
            Message(role="tool", content='{"content": "data"}', tool_call_id="1"),
        ]
        converted = provider._convert_messages(messages)
        assert len(converted) == 4
        assert converted[0]["role"] == "system"
        assert converted[2]["tool_calls"] is not None
        assert converted[3]["tool_call_id"] == "1"


# ---------------------------------------------------------------------------
# Unit tests for crypto module
# ---------------------------------------------------------------------------


class TestCrypto:
    """Tests for credential encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        from codex.agents.crypto import decrypt_value, encrypt_value

        plaintext = "sk-test-1234567890"
        encrypted = encrypt_value(plaintext)
        assert encrypted != plaintext
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_different_values_produce_different_ciphertexts(self):
        from codex.agents.crypto import encrypt_value

        a = encrypt_value("key-a")
        b = encrypt_value("key-b")
        assert a != b


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestAgentAPI:
    """Integration tests for the /api/v1/agents endpoints."""

    def test_create_agent(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()

        response = test_client.post(
            "/api/v1/agents/",
            params={"workspace_id": workspace["id"]},
            json={
                "name": "Research Assistant",
                "provider": "openai",
                "model": "gpt-4o",
                "can_read": True,
                "can_write": True,
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Research Assistant"
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o"
        assert data["can_read"] is True
        assert data["can_write"] is True
        assert data["can_delete"] is False
        assert data["is_active"] is True

    def test_list_agents(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()
        ws_id = workspace["id"]

        # Initially empty
        response = test_client.get("/api/v1/agents/", params={"workspace_id": ws_id}, headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # Create agents
        for name in ["Agent A", "Agent B"]:
            test_client.post(
                "/api/v1/agents/",
                params={"workspace_id": ws_id},
                json={"name": name, "provider": "openai", "model": "gpt-4o"},
                headers=headers,
            )

        response = test_client.get("/api/v1/agents/", params={"workspace_id": ws_id}, headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_agent(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()

        create_resp = test_client.post(
            "/api/v1/agents/",
            params={"workspace_id": workspace["id"]},
            json={"name": "My Agent", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
            headers=headers,
        )
        agent_id = create_resp.json()["id"]

        response = test_client.get(f"/api/v1/agents/{agent_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "My Agent"

    def test_update_agent(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()

        create_resp = test_client.post(
            "/api/v1/agents/",
            params={"workspace_id": workspace["id"]},
            json={"name": "Original", "provider": "openai", "model": "gpt-4o"},
            headers=headers,
        )
        agent_id = create_resp.json()["id"]

        response = test_client.put(
            f"/api/v1/agents/{agent_id}",
            json={"name": "Updated", "can_write": True},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"
        assert response.json()["can_write"] is True

    def test_delete_agent(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()

        create_resp = test_client.post(
            "/api/v1/agents/",
            params={"workspace_id": workspace["id"]},
            json={"name": "To Delete", "provider": "openai", "model": "gpt-4o"},
            headers=headers,
        )
        agent_id = create_resp.json()["id"]

        response = test_client.delete(f"/api/v1/agents/{agent_id}", headers=headers)
        assert response.status_code == 204

        # Verify deleted
        response = test_client.get(f"/api/v1/agents/{agent_id}", headers=headers)
        assert response.status_code == 404

    def test_toggle_agent_active(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()

        create_resp = test_client.post(
            "/api/v1/agents/",
            params={"workspace_id": workspace["id"]},
            json={"name": "Toggle Agent", "provider": "openai", "model": "gpt-4o"},
            headers=headers,
        )
        agent_id = create_resp.json()["id"]
        assert create_resp.json()["is_active"] is True

        # Deactivate
        response = test_client.post(
            f"/api/v1/agents/{agent_id}/activate",
            params={"active": False},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_nonexistent_agent(self, test_client, auth_headers):
        headers = auth_headers[0]
        response = test_client.get("/api/v1/agents/99999", headers=headers)
        assert response.status_code == 404

    def test_requires_auth(self, test_client):
        response = test_client.get("/api/v1/agents/", params={"workspace_id": 1})
        assert response.status_code == 401


class TestAgentCredentialAPI:
    """Integration tests for agent credential endpoints."""

    def _create_agent(self, test_client, headers, workspace_id):
        resp = test_client.post(
            "/api/v1/agents/",
            params={"workspace_id": workspace_id},
            json={"name": "Cred Agent", "provider": "openai", "model": "gpt-4o"},
            headers=headers,
        )
        return resp.json()["id"]

    def test_set_and_list_credentials(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        # Set credential
        response = test_client.post(
            f"/api/v1/agents/{agent_id}/credentials",
            json={"key_name": "api_key", "value": "sk-secret-123"},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key_name"] == "api_key"
        # Value should NOT be returned
        assert "value" not in data
        assert "encrypted_value" not in data

    def test_list_credentials(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        test_client.post(
            f"/api/v1/agents/{agent_id}/credentials",
            json={"key_name": "api_key", "value": "sk-test"},
            headers=headers,
        )

        response = test_client.get(f"/api/v1/agents/{agent_id}/credentials", headers=headers)
        assert response.status_code == 200
        creds = response.json()
        assert len(creds) == 1
        assert creds[0]["key_name"] == "api_key"

    def test_delete_credential(self, test_client, auth_headers, create_workspace):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        test_client.post(
            f"/api/v1/agents/{agent_id}/credentials",
            json={"key_name": "api_key", "value": "sk-test"},
            headers=headers,
        )

        response = test_client.delete(f"/api/v1/agents/{agent_id}/credentials/api_key", headers=headers)
        assert response.status_code == 204

        # Verify deleted
        response = test_client.get(f"/api/v1/agents/{agent_id}/credentials", headers=headers)
        assert len(response.json()) == 0


class TestAgentSessionAPI:
    """Integration tests for agent session endpoints."""

    def _create_agent(self, test_client, headers, workspace_id):
        resp = test_client.post(
            "/api/v1/agents/",
            params={"workspace_id": workspace_id},
            json={"name": "Session Agent", "provider": "openai", "model": "gpt-4o"},
            headers=headers,
        )
        return resp.json()["id"]

    def test_start_session(self, test_client, auth_headers, create_workspace, tmp_path):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        response = test_client.post(
            f"/api/v1/agents/{agent_id}/sessions",
            json={"notebook_path": str(tmp_path)},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"] == agent_id
        assert data["status"] == "pending"

    def test_list_sessions(self, test_client, auth_headers, create_workspace, tmp_path):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        test_client.post(
            f"/api/v1/agents/{agent_id}/sessions",
            json={"notebook_path": str(tmp_path)},
            headers=headers,
        )

        response = test_client.get(f"/api/v1/agents/{agent_id}/sessions", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_session(self, test_client, auth_headers, create_workspace, tmp_path):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        create_resp = test_client.post(
            f"/api/v1/agents/{agent_id}/sessions",
            json={"notebook_path": str(tmp_path)},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        response = test_client.get(f"/api/v1/sessions/{session_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == session_id

    def test_cancel_session(self, test_client, auth_headers, create_workspace, tmp_path):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        create_resp = test_client.post(
            f"/api/v1/agents/{agent_id}/sessions",
            json={"notebook_path": str(tmp_path)},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        response = test_client.post(f"/api/v1/sessions/{session_id}/cancel", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_inactive_agent_cannot_start_session(self, test_client, auth_headers, create_workspace, tmp_path):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        # Deactivate the agent
        test_client.post(f"/api/v1/agents/{agent_id}/activate", params={"active": False}, headers=headers)

        response = test_client.post(
            f"/api/v1/agents/{agent_id}/sessions",
            json={"notebook_path": str(tmp_path)},
            headers=headers,
        )
        assert response.status_code == 400

    def test_session_logs_empty_initially(self, test_client, auth_headers, create_workspace, tmp_path):
        headers = auth_headers[0]
        workspace = create_workspace()
        agent_id = self._create_agent(test_client, headers, workspace["id"])

        create_resp = test_client.post(
            f"/api/v1/agents/{agent_id}/sessions",
            json={"notebook_path": str(tmp_path)},
            headers=headers,
        )
        session_id = create_resp.json()["id"]

        response = test_client.get(f"/api/v1/sessions/{session_id}/logs", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 0
