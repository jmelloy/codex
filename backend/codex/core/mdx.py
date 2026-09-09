"""MDX component registry and content inspection.

Defines the allowlist of custom components that may be referenced from MDX
block content (e.g. ``<Calendar date="2026-01-01" />``). The actual
sandboxing enforcement point is the frontend MDX renderer, which must only
resolve component tags present in its own registry so anything not
registered fails to render instead of executing; that frontend registry does
not exist yet (frontend MDX rendering is later Phase-1/2 work) and must be
kept in sync with this list once it's added.

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
