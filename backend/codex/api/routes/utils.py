"""Shared utility functions for API routes."""

import re


def slugify(name: str, default: str = "item") -> str:
    """Convert a name to a filesystem-safe slug.

    Args:
        name: The name to convert.
        default: Fallback value when the resulting slug is empty.

    Returns:
        A lowercase, hyphen-separated slug safe for use as a filesystem name.
    """
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or default
