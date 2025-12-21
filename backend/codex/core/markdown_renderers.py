"""Plugin system for rendering markdown frontmatter fields.

This module provides an extensible system for rendering different types
of frontmatter data with custom formatters.
"""

from typing import Any, Callable, Dict, Optional


class FrontmatterRenderer:
    """Base class for frontmatter field renderers."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render a frontmatter field value.

        Args:
            value: The value to render
            key: The frontmatter key

        Returns:
            Dictionary with rendering information:
            - type: The render type (text, date, list, link, etc.)
            - value: The formatted value
            - display: Optional display value (for UI)
        """
        raise NotImplementedError


class TextRenderer(FrontmatterRenderer):
    """Renderer for simple text values."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render as text."""
        return {
            "type": "text",
            "value": str(value),
            "display": str(value),
        }


class DateRenderer(FrontmatterRenderer):
    """Renderer for date values."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render as date."""
        from datetime import date, datetime

        if isinstance(value, (date, datetime)):
            return {
                "type": "date",
                "value": value.isoformat(),
                "display": value.strftime("%Y-%m-%d"),
            }
        return {
            "type": "date",
            "value": str(value),
            "display": str(value),
        }


class ListRenderer(FrontmatterRenderer):
    """Renderer for list/array values."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render as list."""
        if not isinstance(value, list):
            value = [value]
        return {
            "type": "list",
            "value": value,
            "display": ", ".join(str(v) for v in value),
        }


class LinkRenderer(FrontmatterRenderer):
    """Renderer for URL/link values."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render as link."""
        return {
            "type": "link",
            "value": str(value),
            "display": str(value),
        }


class BooleanRenderer(FrontmatterRenderer):
    """Renderer for boolean values."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render as boolean."""
        bool_value = bool(value)
        return {
            "type": "boolean",
            "value": bool_value,
            "display": "Yes" if bool_value else "No",
        }


class NumberRenderer(FrontmatterRenderer):
    """Renderer for numeric values."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render as number."""
        return {
            "type": "number",
            "value": value,
            "display": str(value),
        }


class MarkdownRenderer(FrontmatterRenderer):
    """Renderer for markdown content."""

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render as markdown."""
        return {
            "type": "markdown",
            "value": str(value),
            "display": str(value),
        }


class FrontmatterRendererRegistry:
    """Registry for frontmatter field renderers."""

    def __init__(self):
        """Initialize the registry."""
        self._renderers: Dict[str, FrontmatterRenderer] = {}
        self._key_renderers: Dict[str, FrontmatterRenderer] = {}
        self._type_renderers: Dict[type, FrontmatterRenderer] = {}
        self._default_renderer = TextRenderer()

        # Register default renderers
        self._register_defaults()

    def _register_defaults(self):
        """Register default renderers."""
        # Type-based renderers
        self.register_for_type(bool, BooleanRenderer())
        self.register_for_type(int, NumberRenderer())
        self.register_for_type(float, NumberRenderer())
        self.register_for_type(list, ListRenderer())

        # Key-based renderers
        self.register_for_key("date", DateRenderer())
        self.register_for_key("created_at", DateRenderer())
        self.register_for_key("updated_at", DateRenderer())
        self.register_for_key("tags", ListRenderer())
        self.register_for_key("url", LinkRenderer())
        self.register_for_key("link", LinkRenderer())
        self.register_for_key("description", MarkdownRenderer())

    def register_for_key(self, key: str, renderer: FrontmatterRenderer):
        """Register a renderer for a specific frontmatter key.

        Args:
            key: Frontmatter key name
            renderer: Renderer instance
        """
        self._key_renderers[key] = renderer

    def register_for_type(self, value_type: type, renderer: FrontmatterRenderer):
        """Register a renderer for a specific value type.

        Args:
            value_type: Python type
            renderer: Renderer instance
        """
        self._type_renderers[value_type] = renderer

    def register_renderer(self, name: str, renderer: FrontmatterRenderer):
        """Register a named renderer.

        Args:
            name: Renderer name
            renderer: Renderer instance
        """
        self._renderers[name] = renderer

    def get_renderer(self, key: str, value: Any) -> FrontmatterRenderer:
        """Get the appropriate renderer for a key-value pair.

        Priority:
        1. Key-specific renderer
        2. Type-specific renderer
        3. Default text renderer

        Args:
            key: Frontmatter key
            value: Frontmatter value

        Returns:
            Appropriate renderer instance
        """
        # Check for key-specific renderer
        if key in self._key_renderers:
            return self._key_renderers[key]

        # Check for type-specific renderer
        value_type = type(value)
        if value_type in self._type_renderers:
            return self._type_renderers[value_type]

        # Return default renderer
        return self._default_renderer

    def render_field(self, key: str, value: Any) -> Dict[str, Any]:
        """Render a frontmatter field.

        Args:
            key: Frontmatter key
            value: Frontmatter value

        Returns:
            Rendered field data
        """
        renderer = self.get_renderer(key, value)
        result = renderer.render(value, key)
        result["key"] = key
        return result

    def render_frontmatter(self, frontmatter: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Render all fields in frontmatter.

        Args:
            frontmatter: Dictionary of frontmatter data

        Returns:
            Dictionary of rendered fields
        """
        rendered = {}
        for key, value in frontmatter.items():
            rendered[key] = self.render_field(key, value)
        return rendered


# Global registry instance
_registry = FrontmatterRendererRegistry()


def get_registry() -> FrontmatterRendererRegistry:
    """Get the global renderer registry.

    Returns:
        FrontmatterRendererRegistry instance
    """
    return _registry


def register_renderer_for_key(key: str, renderer: FrontmatterRenderer):
    """Register a renderer for a specific key in the global registry.

    Args:
        key: Frontmatter key name
        renderer: Renderer instance
    """
    _registry.register_for_key(key, renderer)


def register_renderer_for_type(value_type: type, renderer: FrontmatterRenderer):
    """Register a renderer for a type in the global registry.

    Args:
        value_type: Python type
        renderer: Renderer instance
    """
    _registry.register_for_type(value_type, renderer)
