"""MDX component registry and content inspection.

Defines the allowlist of custom components that may be referenced from MDX
block content (e.g. ``<Calendar date="2026-01-01" />``). This is the backend
mirror of the frontend registry in frontend/src/mdx/componentRegistry.ts,
which is the actual sandboxing enforcement point: the MDX-to-Vue runtime only
resolves component tags present in that registry, so anything not registered
fails to render instead of executing. Keep both lists in sync when adding or
removing components.

This module lets the API flag unauthorized component usage before content is
ever served to a client, and gives tests/tools a single source of truth for
"what components exist" without needing a browser.
"""

import re

MDX_COMPONENT_REGISTRY: dict[str, str] = {
    "Calendar": "Displays a date or date range on a calendar",
    "CodeBlock": "Syntax-highlighted code with an optional filename/language",
    "Weather": "Current weather and forecast for a location",
    "LinkPreview": "Unfurled preview card for a URL",
    "GitHubIssues": "List of issues from a GitHub repository",
    "GitHubPulls": "List of pull requests from a GitHub repository",
    "GitHubRepo": "GitHub repository summary card",
    "ApiBlock": "Fetch and display data from a REST API endpoint",
    "DatabaseBlock": "Query the notebook database and display results",
}

ALLOWED_COMPONENTS: set[str] = set(MDX_COMPONENT_REGISTRY)

# Matches capitalized JSX-style tags, e.g. `<Calendar` or `</Calendar>`.
# Component names must start with an uppercase letter per the JSX/MDX
# convention that distinguishes components from lowercase host HTML elements.
_COMPONENT_TAG_RE = re.compile(r"</?([A-Z][A-Za-z0-9]*)\b")


def extract_component_names(mdx_source: str) -> set[str]:
    """Return the set of capitalized JSX-style component tags referenced in MDX source."""
    return set(_COMPONENT_TAG_RE.findall(mdx_source))


def find_unauthorized_components(mdx_source: str) -> set[str]:
    """Return component tags referenced in MDX source that are not in the allowlist."""
    return extract_component_names(mdx_source) - ALLOWED_COMPONENTS
