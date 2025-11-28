"""Utility functions for Lab Notebook."""

import re


def slugify(text: str) -> str:
    """Convert title to filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")
