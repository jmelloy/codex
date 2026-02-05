"""Integration tests for template API endpoints."""

from datetime import datetime
from pathlib import Path


def setup_custom_template(test_client, headers, workspace, notebook, template_id, template_content):
    """Create a custom template in the notebook's .templates folder."""
    ws_detail = test_client.get(
        f"/api/v1/workspaces/{workspace['slug']}",
        headers=headers,
    )
    assert ws_detail.status_code == 200
    workspace_path = Path(ws_detail.json()["path"])
    notebook_path = workspace_path / notebook["path"]

    # Create .templates folder and a custom template
    templates_dir = notebook_path / ".templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    template_file = templates_dir / f"{template_id}.md"
    template_file.write_text(template_content)

    return notebook_path


def test_create_from_custom_template(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file from a custom template in .templates folder."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a simple custom template
    template_content = """---
type: template
template_for: .md
default_name: "simple-note.md"
template_content: "# Simple Note\\n\\nContent here"
---

Template definition file.
"""
    notebook_path = Path(setup_custom_template(test_client, headers, workspace, notebook, "simple-template", template_content)).resolve()

    # Create file from custom template
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/from-template",
        json={
            "template_id": "simple-template",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert "notebook_id" in data
    assert data["notebook_id"] == notebook["id"]
    assert "path" in data
    assert "filename" in data
    assert data["content_type"] == "text/markdown"
    assert data["size"] > 0
    assert "message" in data
    assert "template" in data["message"].lower()

    # Verify file was created
    file_path = notebook_path / data["path"]
    assert file_path.exists()
    content = file_path.read_text()
    assert "# Simple Note" in content


def test_create_from_template_with_custom_filename(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file from a template with a custom filename."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a custom template
    template_content = """---
type: template
template_for: .md
default_name: "default-{yyyy}.md"
template_content: "# Custom Filename Test"
---
"""
    setup_custom_template(test_client, headers, workspace, notebook, "filename-test", template_content)

    # Create file from template with custom filename
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/from-template",
        json={
            "template_id": "filename-test",
            "filename": "my-custom-note",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Verify custom filename was used
    assert "my-custom-note.md" == data["filename"]


def test_create_from_template_invalid_template(test_client, auth_headers, workspace_and_notebook):
    """Test that creating from a non-existent template returns 404."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Try to create file from non-existent template
    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/from-template",
        json={
            "template_id": "non-existent-template-xyz",
        },
        headers=headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_from_template_duplicate_file(test_client, auth_headers, workspace_and_notebook):
    """Test that creating from a template when file exists returns 400."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a custom template with a fixed filename (no pattern)
    template_content = """---
type: template
template_for: .md
default_name: "duplicate.md"
template_content: "# Duplicate Test\\n\\nThis is a duplicate test."
---

This is the template definition file.
"""
    setup_custom_template(test_client, headers, workspace, notebook, "dup-test", template_content)

    # Create file from template with custom filename
    response1 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/from-template",
        json={
            "template_id": "dup-test",
            "filename": "duplicate-test",
        },
        headers=headers,
    )
    assert response1.status_code == 200

    # Try to create same file again
    response2 = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/from-template",
        json={
            "template_id": "dup-test",
            "filename": "duplicate-test",
        },
        headers=headers,
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()


def test_create_from_template_with_nested_path(test_client, auth_headers, workspace_and_notebook):
    """Test creating a file from a template with nested directory in filename."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a template with nested path pattern
    template_content = """---
type: template
template_for: .md
default_name: "{yyyy}/{mm}/note-{dd}.md"
template_content: "# Nested Path Test"
---
"""
    notebook_path = setup_custom_template(test_client, headers, workspace, notebook, "nested-test", template_content)

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/from-template",
        json={
            "template_id": "nested-test",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Verify nested path was created
    assert "/" in data["path"]

    # Verify the file actually exists at that path
    file_path = Path(notebook_path) / data["path"]
    assert file_path.exists()


def test_template_pattern_expansion(test_client, auth_headers, workspace_and_notebook):
    """Test that template patterns are properly expanded with current date."""
    headers = auth_headers[0]
    workspace, notebook = workspace_and_notebook

    # Create a template with all pattern types (using single-line for simplicity)
    template_content = """---
type: template
template_for: .md
default_name: "pattern-test.md"
template_content: "---\\ntitle: {title}\\nyear: {yyyy}\\nmonth: {mm}\\nday: {dd}\\nmonth_name: {month}\\nmonth_abbr: {mon}\\n---\\n\\n# Pattern Expansion Test\\n\\nYear: {yyyy}\\nMonth: {mm} ({month})\\nDay: {dd}"
---
"""
    notebook_path = Path(setup_custom_template(test_client, headers, workspace, notebook, "pattern-test", template_content)).resolve()

    response = test_client.post(
        f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/files/from-template",
        json={
            "template_id": "pattern-test",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Get the file content to verify pattern expansion
    file_path = notebook_path / data["path"]
    content = file_path.read_text()

    # Verify date patterns were expanded
    now = datetime.now()
    assert now.strftime("%Y") in content
    assert now.strftime("%m") in content
    assert now.strftime("%d") in content
    assert now.strftime("%B") in content  # Full month name
    assert now.strftime("%b") in content  # Abbreviated month name
