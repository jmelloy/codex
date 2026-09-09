"""Tests for the MDX -> Typst transformer and PDF export pipeline (issue #593, Phase 3)."""

from codex.core.typst_export import (
    TypstCompileError,
    compile_typst_to_pdf,
    escape_typst_text,
    export_content_to_pdf,
    fallback_box,
    mdx_to_typst,
    render_typst_document,
)


class TestEscaping:
    def test_escapes_special_characters(self):
        assert escape_typst_text("a#b$c@d_e*f`g<h>i[j]k") == r"a\#b\$c\@d\_e\*f\`g\<h\>i\[j\]k"

    def test_leaves_plain_text_untouched(self):
        assert escape_typst_text("Hello world 123") == "Hello world 123"


class TestMdxToTypst:
    def test_headings(self):
        result = mdx_to_typst("# Title\n\n## Subtitle\n\n### H3")
        assert "= Title" in result
        assert "== Subtitle" in result
        assert "=== H3" in result

    def test_bold_and_italic(self):
        result = mdx_to_typst("This is **bold** and *italic* and __also bold__ and _also italic_.")
        assert "*bold*" in result
        assert "_italic_" in result
        assert "*also bold*" in result
        assert "_also italic_" in result

    def test_unordered_list(self):
        result = mdx_to_typst("- one\n- two\n- three")
        assert result.splitlines() == ["- one", "- two", "- three"]

    def test_ordered_list(self):
        result = mdx_to_typst("1. one\n2. two")
        assert result.splitlines() == ["+ one", "+ two"]

    def test_blockquote(self):
        result = mdx_to_typst("> a wise quote\n> spanning two lines")
        assert result == "#quote(block: true)[a wise quote spanning two lines]"

    def test_horizontal_rule(self):
        assert mdx_to_typst("---") == "#line(length: 100%)"

    def test_inline_code_not_escaped(self):
        result = mdx_to_typst("Run `git status --short` now")
        assert "`git status --short`" in result

    def test_link(self):
        result = mdx_to_typst("See [the docs](https://example.com/docs)")
        assert '#link("https://example.com/docs")[the docs]' in result

    def test_image_gets_text_fallback(self):
        result = mdx_to_typst("![a diagram](diagram.png)")
        assert "_[Image: a diagram]_" in result

    def test_fenced_code_block_passes_through(self):
        content = "Some text\n\n```python\ndef f():\n    return 1\n```\n\nMore text"
        result = mdx_to_typst(content)
        assert "```python\ndef f():\n    return 1\n```" in result

    def test_fenced_code_block_contents_not_treated_as_markdown(self):
        content = "```python\n# not a heading\n- not a list\n```"
        result = mdx_to_typst(content)
        assert "# not a heading" in result
        assert "- not a list" in result
        assert "=" not in result.split("```")[0]  # nothing before the fence

    def test_special_characters_in_plain_text_are_escaped(self):
        result = mdx_to_typst("Cost is $5 and uses a #tag and an @mention")
        assert r"\$5" in result
        assert r"\#tag" in result
        assert r"\@mention" in result

    def test_known_component_gets_labeled_fallback_box(self):
        result = mdx_to_typst('Hello <Calendar date="2026-01-01" />')
        assert "#block(" in result
        assert "Calendar component" in result
        assert "date: 2026-01-01" in result

    def test_component_directive_is_not_escaped_by_surrounding_inline_conversion(self):
        # Component tags are frequently mid-paragraph, so the fallback box they
        # expand to must survive `_convert_inline()`'s escaping of the same
        # `#`/`[`/`]` characters the directive is built from.
        result = mdx_to_typst('Hello <Calendar date="2026-01-01" /> world')
        assert "\\#block(" not in result
        assert "\\[" not in result
        assert "\\]" not in result
        assert result.startswith("Hello #block(")
        assert result.rstrip().endswith("] world") or "] world" in result

    def test_unknown_component_gets_generic_fallback_box(self):
        result = mdx_to_typst('<EvilScript src="x" />')
        assert "EvilScript component" in result
        assert "Unrecognized component" in result

    def test_paired_component_tag(self):
        result = mdx_to_typst("<CodeBlock>ignored children</CodeBlock>")
        assert "CodeBlock component" in result


class TestRenderTypstDocument:
    def test_includes_title_as_heading(self):
        doc = render_typst_document("body text", title="My Page")
        assert "= My Page" in doc
        assert "body text" in doc

    def test_escapes_quotes_in_title_string_literal(self):
        doc = render_typst_document("body", title='Say "hi"')
        assert '#set document(title: "Say \\"hi\\"")' in doc

    def test_no_title_still_produces_valid_header(self):
        doc = render_typst_document("body text")
        assert "#set page(margin: 1in)" in doc
        assert "body text" in doc


class TestCompileTypstToPdf:
    def test_compiles_simple_document_to_pdf_bytes(self):
        pdf_bytes = compile_typst_to_pdf("= Hello\n\nThis is a test.")
        assert pdf_bytes.startswith(b"%PDF")

    def test_raises_typst_compile_error_on_invalid_syntax(self):
        try:
            compile_typst_to_pdf("#this-is-not-valid-typst-syntax(((")
            raise AssertionError("expected TypstCompileError")
        except TypstCompileError:
            pass

    def test_export_content_to_pdf_end_to_end(self):
        pdf_bytes = export_content_to_pdf("# Heading\n\nSome **bold** text.", title="Doc Title")
        assert pdf_bytes.startswith(b"%PDF")


class TestFallbackBox:
    def test_includes_heading_and_details(self):
        box = fallback_box("Weather component", "shows a forecast", {"location": "NYC"})
        assert "Weather component" in box
        assert "shows a forecast" in box
        assert "location: NYC" in box

    def test_escapes_detail_values(self):
        box = fallback_box("Thing", details={"note": "a # in a value"})
        assert r"a \# in a value" in box


class TestExportEndpoint:
    def test_export_leaf_block_returns_pdf(self, test_client, auth_headers, workspace_and_notebook):
        headers = auth_headers[0]
        workspace, notebook = workspace_and_notebook
        base = f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks"

        page = test_client.post(f"{base}/pages", json={"title": "Export Page"}, headers=headers).json()
        block = test_client.post(
            base + "/",
            json={"parent_block_id": page["block_id"], "block_type": "text", "content": "# Hi\n\nSome **text**."},
            headers=headers,
        ).json()

        response = test_client.get(f"{base}/{block['block_id']}/export/pdf", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    def test_export_page_includes_children(self, test_client, auth_headers, workspace_and_notebook):
        headers = auth_headers[0]
        workspace, notebook = workspace_and_notebook
        base = f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks"

        page = test_client.post(f"{base}/pages", json={"title": "Whole Page Export"}, headers=headers).json()
        test_client.post(
            base + "/",
            json={"parent_block_id": page["block_id"], "block_type": "text", "content": "Child block content"},
            headers=headers,
        )

        response = test_client.get(f"{base}/{page['block_id']}/export/pdf", headers=headers)
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")

    def test_export_unknown_block_returns_404(self, test_client, auth_headers, workspace_and_notebook):
        headers = auth_headers[0]
        workspace, notebook = workspace_and_notebook
        base = f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks"

        response = test_client.get(f"{base}/does-not-exist/export/pdf", headers=headers)
        assert response.status_code == 404

    def test_export_sanitizes_malicious_title_in_content_disposition(
        self, test_client, auth_headers, workspace_and_notebook
    ):
        headers = auth_headers[0]
        workspace, notebook = workspace_and_notebook
        base = f"/api/v1/workspaces/{workspace['slug']}/notebooks/{notebook['slug']}/blocks"

        page = test_client.post(
            f"{base}/pages",
            json={"title": 'evil"\r\nX-Injected: yes\r\n/../../etc/passwd'},
            headers=headers,
        ).json()

        response = test_client.get(f"{base}/{page['block_id']}/export/pdf", headers=headers)
        assert response.status_code == 200
        disposition = response.headers["content-disposition"]
        # No CR/LF means the malicious title can't terminate the header and
        # inject a second one (e.g. the embedded "X-Injected: yes" line).
        assert "\r" not in disposition
        assert "\n" not in disposition
        assert "/" not in disposition
        assert disposition.startswith('attachment; filename="')
        assert "filename*=UTF-8''" in disposition
        # Only one Content-Disposition header made it through - not split into two.
        assert len(response.headers.get_list("content-disposition")) == 1
