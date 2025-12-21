"""Tests for markdown frontmatter renderers."""

import pytest

from codex.core.markdown_renderers import (
    BooleanRenderer,
    DateRenderer,
    FrontmatterRendererRegistry,
    LinkRenderer,
    ListRenderer,
    MarkdownRenderer,
    NumberRenderer,
    TextRenderer,
    get_registry,
)


class TestTextRenderer:
    """Test TextRenderer class."""

    def test_render_string(self):
        """Test rendering a string value."""
        renderer = TextRenderer()
        result = renderer.render("Hello, World!", "title")
        assert result["type"] == "text"
        assert result["value"] == "Hello, World!"
        assert result["display"] == "Hello, World!"

    def test_render_number(self):
        """Test rendering a number as text."""
        renderer = TextRenderer()
        result = renderer.render(42, "age")
        assert result["type"] == "text"
        assert result["value"] == "42"


class TestDateRenderer:
    """Test DateRenderer class."""

    def test_render_date_string(self):
        """Test rendering a date string."""
        renderer = DateRenderer()
        result = renderer.render("2024-12-20", "date")
        assert result["type"] == "date"
        assert result["value"] == "2024-12-20"
        assert result["display"] == "2024-12-20"


class TestListRenderer:
    """Test ListRenderer class."""

    def test_render_list(self):
        """Test rendering a list."""
        renderer = ListRenderer()
        result = renderer.render(["tag1", "tag2", "tag3"], "tags")
        assert result["type"] == "list"
        assert result["value"] == ["tag1", "tag2", "tag3"]
        assert result["display"] == "tag1, tag2, tag3"

    def test_render_single_value_as_list(self):
        """Test rendering a single value as a list."""
        renderer = ListRenderer()
        result = renderer.render("single", "tags")
        assert result["type"] == "list"
        assert result["value"] == ["single"]
        assert result["display"] == "single"


class TestBooleanRenderer:
    """Test BooleanRenderer class."""

    def test_render_true(self):
        """Test rendering True."""
        renderer = BooleanRenderer()
        result = renderer.render(True, "active")
        assert result["type"] == "boolean"
        assert result["value"] is True
        assert result["display"] == "Yes"

    def test_render_false(self):
        """Test rendering False."""
        renderer = BooleanRenderer()
        result = renderer.render(False, "active")
        assert result["type"] == "boolean"
        assert result["value"] is False
        assert result["display"] == "No"


class TestNumberRenderer:
    """Test NumberRenderer class."""

    def test_render_integer(self):
        """Test rendering an integer."""
        renderer = NumberRenderer()
        result = renderer.render(42, "count")
        assert result["type"] == "number"
        assert result["value"] == 42
        assert result["display"] == "42"

    def test_render_float(self):
        """Test rendering a float."""
        renderer = NumberRenderer()
        result = renderer.render(3.14, "pi")
        assert result["type"] == "number"
        assert result["value"] == 3.14
        assert result["display"] == "3.14"


class TestLinkRenderer:
    """Test LinkRenderer class."""

    def test_render_url(self):
        """Test rendering a URL."""
        renderer = LinkRenderer()
        result = renderer.render("https://example.com", "url")
        assert result["type"] == "link"
        assert result["value"] == "https://example.com"
        assert result["display"] == "https://example.com"


class TestMarkdownRenderer:
    """Test MarkdownRenderer class."""

    def test_render_markdown(self):
        """Test rendering markdown content."""
        renderer = MarkdownRenderer()
        result = renderer.render("# Heading\n\nContent", "description")
        assert result["type"] == "markdown"
        assert "# Heading" in result["value"]


class TestFrontmatterRendererRegistry:
    """Test FrontmatterRendererRegistry class."""

    def test_default_registry_initialization(self):
        """Test that default registry is properly initialized."""
        registry = FrontmatterRendererRegistry()
        
        # Check type-based renderers
        assert registry.get_renderer("test", True).__class__ == BooleanRenderer
        assert registry.get_renderer("test", 42).__class__ == NumberRenderer
        assert registry.get_renderer("test", ["a", "b"]).__class__ == ListRenderer

    def test_key_based_renderer(self):
        """Test key-based renderer selection."""
        registry = FrontmatterRendererRegistry()
        
        # Date keys should use DateRenderer
        assert registry.get_renderer("date", "2024-12-20").__class__ == DateRenderer
        assert registry.get_renderer("created_at", "2024-12-20").__class__ == DateRenderer
        
        # Tags should use ListRenderer
        assert registry.get_renderer("tags", ["a", "b"]).__class__ == ListRenderer

    def test_custom_renderer_registration(self):
        """Test registering a custom renderer."""
        registry = FrontmatterRendererRegistry()
        custom_renderer = TextRenderer()
        registry.register_for_key("custom_field", custom_renderer)
        
        assert registry.get_renderer("custom_field", "value") == custom_renderer

    def test_render_field(self):
        """Test rendering a single field."""
        registry = FrontmatterRendererRegistry()
        result = registry.render_field("title", "Test Title")
        
        assert result["key"] == "title"
        assert result["type"] == "text"
        assert result["value"] == "Test Title"
        assert result["display"] == "Test Title"

    def test_render_frontmatter(self):
        """Test rendering complete frontmatter."""
        registry = FrontmatterRendererRegistry()
        frontmatter = {
            "title": "Test Document",
            "date": "2024-12-20",
            "tags": ["test", "demo"],
            "count": 42,
            "active": True,
        }
        
        rendered = registry.render_frontmatter(frontmatter)
        
        # Check all fields are rendered
        assert "title" in rendered
        assert "date" in rendered
        assert "tags" in rendered
        assert "count" in rendered
        assert "active" in rendered
        
        # Check types
        assert rendered["title"]["type"] == "text"
        assert rendered["date"]["type"] == "date"
        assert rendered["tags"]["type"] == "list"
        assert rendered["count"]["type"] == "number"
        assert rendered["active"]["type"] == "boolean"
        
        # Check values
        assert rendered["title"]["value"] == "Test Document"
        assert rendered["date"]["value"] == "2024-12-20"
        assert rendered["tags"]["value"] == ["test", "demo"]
        assert rendered["count"]["value"] == 42
        assert rendered["active"]["value"] is True


class TestGlobalRegistry:
    """Test global registry functions."""

    def test_get_registry(self):
        """Test getting the global registry."""
        registry = get_registry()
        assert isinstance(registry, FrontmatterRendererRegistry)
        
        # Should return the same instance
        assert get_registry() is registry
