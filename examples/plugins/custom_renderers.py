"""Example custom renderer plugin for Codex markdown frontmatter.

This example shows how to create and register custom renderers for
displaying frontmatter fields in a specialized way.
"""

from typing import Any, Dict

from codex.core.markdown_renderers import (
    FrontmatterRenderer,
    register_renderer_for_key,
)


class StatusRenderer(FrontmatterRenderer):
    """Renderer for status fields with color coding."""

    STATUS_CONFIG = {
        "draft": {"color": "#6b7280", "icon": "📝"},
        "in_progress": {"color": "#3b82f6", "icon": "🔄"},
        "review": {"color": "#f59e0b", "icon": "👀"},
        "published": {"color": "#10b981", "icon": "✅"},
        "archived": {"color": "#ef4444", "icon": "��"},
    }

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render status with color and icon."""
        status = str(value).lower().replace(" ", "_")
        config = self.STATUS_CONFIG.get(status, {"color": "#6b7280", "icon": "❓"})

        return {
            "type": "status",
            "value": status,
            "display": f"{config['icon']} {status.replace('_', ' ').title()}",
            "color": config["color"],
        }


class PriorityRenderer(FrontmatterRenderer):
    """Renderer for priority fields with level indicators."""

    PRIORITY_LEVELS = {
        "critical": {"level": 5, "color": "#dc2626", "icon": "🔥"},
        "high": {"level": 4, "color": "#ef4444", "icon": "⚠️"},
        "medium": {"level": 3, "color": "#f59e0b", "icon": "➡️"},
        "low": {"level": 2, "color": "#10b981", "icon": "⬇️"},
        "none": {"level": 1, "color": "#6b7280", "icon": "➖"},
    }

    def render(self, value: Any, key: str) -> Dict[str, Any]:
        """Render priority with level and color."""
        priority = str(value).lower()
        config = self.PRIORITY_LEVELS.get(priority, self.PRIORITY_LEVELS["none"])

        return {
            "type": "priority",
            "value": priority,
            "display": f"{config['icon']} {priority.title()}",
            "level": config["level"],
            "color": config["color"],
        }


def register_example_renderers():
    """Register all example custom renderers.

    Call this function at application startup to enable custom renderers.
    """
    register_renderer_for_key("status", StatusRenderer())
    register_renderer_for_key("priority", PriorityRenderer())
