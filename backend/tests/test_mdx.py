"""Tests for MDX core infrastructure: content_format defaults/migration,
Block.render(), and the component registry security model."""

from sqlalchemy import text

from codex.core.blocks import create_block, create_page
from codex.core.mdx import MDX_COMPONENT_REGISTRY
from codex.db.database import get_notebook_session, init_notebook_db
from codex.db.models import Block


def _init_notebook(tmp_path):
    notebook_path = tmp_path / "nb"
    notebook_path.mkdir()
    init_notebook_db(str(notebook_path))
    return notebook_path


class TestContentFormatDefaults:
    def test_new_page_defaults_to_mdx(self, tmp_path):
        notebook_path = _init_notebook(tmp_path)
        nb_session = get_notebook_session(str(notebook_path))
        try:
            result = create_page(
                notebook_path=notebook_path,
                notebook_id=1,
                parent_path=None,
                title="My Page",
                nb_session=nb_session,
            )
            from sqlmodel import select

            page_block = nb_session.exec(select(Block).where(Block.block_id == result["block_id"])).first()
            assert page_block.content_format == "mdx"
        finally:
            nb_session.close()

    def test_new_block_defaults_to_mdx(self, tmp_path):
        notebook_path = _init_notebook(tmp_path)
        nb_session = get_notebook_session(str(notebook_path))
        try:
            page = create_page(
                notebook_path=notebook_path,
                notebook_id=1,
                parent_path=None,
                title="My Page",
                nb_session=nb_session,
            )
            result = create_block(
                notebook_path=notebook_path,
                notebook_id=1,
                page_path=page["path"],
                block_type="text",
                content="Hello",
                nb_session=nb_session,
            )
            from sqlmodel import select

            block = nb_session.exec(select(Block).where(Block.block_id == result["block_id"])).first()
            assert block.content_format == "mdx"
        finally:
            nb_session.close()

    def test_create_block_rejects_invalid_content_format(self, tmp_path):
        notebook_path = _init_notebook(tmp_path)
        nb_session = get_notebook_session(str(notebook_path))
        try:
            page = create_page(
                notebook_path=notebook_path,
                notebook_id=1,
                parent_path=None,
                title="My Page",
                nb_session=nb_session,
            )
            try:
                create_block(
                    notebook_path=notebook_path,
                    notebook_id=1,
                    page_path=page["path"],
                    block_type="text",
                    content="Hello",
                    content_format="not-a-real-format",
                    nb_session=nb_session,
                )
                raise AssertionError("expected ValueError")
            except ValueError:
                pass
        finally:
            nb_session.close()

    def test_explicit_legacy_content_format_is_preserved(self, tmp_path):
        notebook_path = _init_notebook(tmp_path)
        nb_session = get_notebook_session(str(notebook_path))
        try:
            page = create_page(
                notebook_path=notebook_path,
                notebook_id=1,
                parent_path=None,
                title="My Page",
                nb_session=nb_session,
            )
            result = create_block(
                notebook_path=notebook_path,
                notebook_id=1,
                page_path=page["path"],
                block_type="text",
                content="Hello",
                content_format="legacy",
                nb_session=nb_session,
            )
            from sqlmodel import select

            block = nb_session.exec(select(Block).where(Block.block_id == result["block_id"])).first()
            assert block.content_format == "legacy"
        finally:
            nb_session.close()


class TestMigrationBackfill:
    def test_markdown_content_format_backfilled_to_legacy(self, tmp_path):
        """A notebook DB stamped at migration 011 (pre-backfill) with a
        content_format='markdown' row should have that row backfilled to
        'legacy' when init_notebook_db() runs migration 012 against it."""
        notebook_path = tmp_path / "nb"
        notebook_path.mkdir()

        # Get to a fully migrated DB first (012 has no schema change, so this
        # gives us the right table shape), then roll the stamped version back
        # to 011 and insert a pre-backfill row.
        engine = init_notebook_db(str(notebook_path))
        with engine.connect() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '011'"))
            conn.execute(
                text(
                    "INSERT INTO blocks "
                    "(notebook_id, block_id, path, block_type, content_format, order_index, "
                    "filename, created_at, updated_at) "
                    "VALUES (1, 'blk-1', 'page/blk-1.md', 'text', 'markdown', 1.0, "
                    "'blk-1.md', '2025-01-01T00:00:00', '2025-01-01T00:00:00')"
                )
            )
            conn.commit()
        engine.dispose()

        # Re-running init applies migration 012 for real against the stamped-011 DB.
        engine = init_notebook_db(str(notebook_path))
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert version == "012"
            row = conn.execute(text("SELECT content_format FROM blocks WHERE block_id = 'blk-1'")).first()
            assert row[0] == "legacy"
        engine.dispose()


class TestBlockRender:
    def _block(self, content_format: str, path: str = "page/blk.md") -> Block:
        return Block(
            notebook_id=1,
            block_id="blk-1",
            path=path,
            block_type="text",
            content_format=content_format,
        )

    def test_render_strips_frontmatter_for_mdx(self):
        block = self._block("mdx")
        raw = '---\ntitle: Hi\n---\n\nHello <Calendar date="2026-01-01" />'
        rendered = block.render(raw)
        assert rendered["content_format"] == "mdx"
        assert rendered["properties"] == {"title": "Hi"}
        assert "title:" not in rendered["content"]
        assert "<Calendar" in rendered["content"]

    def test_render_strips_frontmatter_for_legacy(self):
        block = self._block("legacy")
        raw = "---\ntitle: Hi\n---\n\nHello world"
        rendered = block.render(raw)
        assert rendered["content_format"] == "legacy"
        assert rendered["properties"] == {"title": "Hi"}

    def test_render_passes_through_json_unchanged(self):
        block = self._block("json", path="page/blk.json")
        raw = '{"a": 1}'
        rendered = block.render(raw)
        assert rendered["content"] == raw
        assert rendered["properties"] == {}


class TestComponentRegistry:
    def test_registry_matches_documented_components(self):
        assert set(MDX_COMPONENT_REGISTRY) == {
            "Calendar",
            "CodeBlock",
            "Weather",
            "LinkPreview",
            "GitHubIssues",
            "GitHubPulls",
            "GitHubRepo",
            "ApiBlock",
            "DatabaseBlock",
        }


from codex.core.mdx import validate_mdx  # noqa: E402


class TestValidateMdx:
    def test_valid_content(self):
        assert validate_mdx('# Hi\n\n<Calendar date="2026-01-01" />\n\n<CodeBlock language="py">\nx\n</CodeBlock>') == []

    def test_plain_markdown_is_valid(self):
        assert validate_mdx("Some **bold** text and `{code}`.") == []

    def test_unknown_component(self):
        issues = validate_mdx("<Evil />")
        assert len(issues) == 1
        assert "Unknown component" in issues[0].message
        assert (issues[0].line, issues[0].column) == (1, 1)

    def test_unclosed_tag(self):
        issues = validate_mdx("text\n<CodeBlock>\nbody")
        assert any("closing tag for <CodeBlock>" in i.message and i.line == 2 for i in issues)

    def test_unexpected_closing_tag(self):
        issues = validate_mdx("</Calendar>")
        assert any("Unexpected closing tag" in i.message for i in issues)

    def test_js_expression_rejected(self):
        issues = validate_mdx("Total: {1 + 1}")
        assert any("JS expressions" in i.message for i in issues)

    def test_escaped_brace_and_code_ignored(self):
        assert validate_mdx("literal \\{ brace and `{x}`\n\n```js\nconst a = {};\n<Evil/>\n```") == []

    def test_import_rejected(self):
        assert any("import/export" in i.message for i in validate_mdx('import x from "y"'))

    def test_dangerous_html_rejected(self):
        assert validate_mdx("<script>alert(1)</script>")
        assert any("event handler" in i.message for i in validate_mdx('<a onclick="x()">hi</a>'))

    def test_malformed_tag(self):
        assert any("Malformed" in i.message for i in validate_mdx('<Calendar date="x"'))


class TestValidateMdxEndpoint:
    def test_valid(self, test_client, auth_headers, workspace_and_notebook):
        ws, nb = workspace_and_notebook
        r = test_client.post(
            f"/api/v1/workspaces/{ws['slug']}/notebooks/{nb['slug']}/blocks/validate-mdx",
            json={"content": "# ok\n<Calendar />"},
            headers=auth_headers[0],
        )
        assert r.status_code == 200
        assert r.json() == {"valid": True, "errors": []}

    def test_invalid(self, test_client, auth_headers, workspace_and_notebook):
        ws, nb = workspace_and_notebook
        r = test_client.post(
            f"/api/v1/workspaces/{ws['slug']}/notebooks/{nb['slug']}/blocks/validate-mdx",
            json={"content": "<Nope>"},
            headers=auth_headers[0],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert body["errors"][0]["line"] == 1

    def test_requires_auth(self, test_client, workspace_and_notebook):
        ws, nb = workspace_and_notebook
        test_client.cookies.clear()
        r = test_client.post(
            f"/api/v1/workspaces/{ws['slug']}/notebooks/{nb['slug']}/blocks/validate-mdx", json={"content": "x"}
        )
        assert r.status_code in (401, 403)
