"""MDX component registry.

The custom components that may be referenced from MDX block content (e.g.
``<Calendar date="2026-01-01" />``). Enforcement happens in the frontend MDX
renderer (frontend/src/services/mdxComponentRegistry.ts mirrors this list),
which renders anything unregistered as a placeholder instead of executing it.
The backend uses the descriptions for PDF export fallbacks.
"""

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
