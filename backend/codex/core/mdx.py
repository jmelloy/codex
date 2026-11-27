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


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

import re  # noqa: E402
from dataclasses import dataclass  # noqa: E402

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# <Name attr="x" />, <Name>, </Name>; attribute values may contain ">" inside quotes.
_JSX_TAG_RE = re.compile(r"<(/?)([A-Z][A-Za-z0-9]*)((?:\"[^\"]*\"|'[^']*'|[^<>\"'])*?)(/?)>")
_BAD_TAG_OPEN_RE = re.compile(r"<(/?)([A-Z][A-Za-z0-9]*)\b")
_ESM_RE = re.compile(r"^\s*(import|export)\s")
_EVENT_HANDLER_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
_DISALLOWED_HOST_TAGS = {"script", "style", "iframe", "object", "embed", "form", "base", "meta", "link"}
_HOST_TAG_RE = re.compile(r"<\s*(" + "|".join(sorted(_DISALLOWED_HOST_TAGS)) + r")\b", re.IGNORECASE)


@dataclass
class MdxIssue:
    """A single problem found in MDX source. ``line``/``column`` are 1-based."""

    message: str
    line: int
    column: int
    severity: str = "error"  # "error" | "warning"

    def to_dict(self) -> dict:
        return {"message": self.message, "line": self.line, "column": self.column, "severity": self.severity}


def validate_mdx(content: str) -> list[MdxIssue]:
    """Lightweight structural validation of MDX source.

    Mirrors the frontend's security model (see mdxRenderer.ts): JS expressions,
    import/export, event handlers and script-bearing HTML are errors; unknown
    capitalized components are errors; JSX tags must be balanced. Fenced and
    inline code is ignored. This is not a full MDX parser - the frontend
    compiler remains authoritative - but it catches the common mistakes with
    line/column positions.
    """
    issues: list[MdxIssue] = []
    stack: list[tuple[str, int, int]] = []
    in_fence = False

    for lineno, raw in enumerate(content.split("\n"), start=1):
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _ESM_RE.match(raw):
            issues.append(MdxIssue("import/export statements are not allowed in MDX content", lineno, 1))
            continue

        # Blank out inline code so its contents aren't parsed, preserving columns.
        line = _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), raw)

        for m in re.finditer(r"(?<!\\)\{", line):
            issues.append(MdxIssue("JS expressions ({...}) are not allowed; escape a literal brace as \\{", lineno, m.start() + 1))
        for m in _HOST_TAG_RE.finditer(line):
            issues.append(MdxIssue(f"<{m.group(1).lower()}> elements are not allowed", lineno, m.start() + 1))
        for m in _EVENT_HANDLER_RE.finditer(line):
            issues.append(MdxIssue("event handler attributes (on*) are not allowed", lineno, m.start() + 2))

        tag_spans = []
        for m in _JSX_TAG_RE.finditer(line):
            tag_spans.append(m.start())
            closing, name, _attrs, self_closing = m.group(1), m.group(2), m.group(3), m.group(4)
            col = m.start() + 1
            if name not in MDX_COMPONENT_REGISTRY:
                issues.append(
                    MdxIssue(
                        f'Unknown component "{name}". Allowed: {", ".join(sorted(MDX_COMPONENT_REGISTRY))}',
                        lineno,
                        col,
                    )
                )
            if closing:
                if stack and stack[-1][0] == name:
                    stack.pop()
                elif any(s[0] == name for s in stack):
                    expected = stack[-1][0]
                    issues.append(MdxIssue(f"Expected a closing tag for <{expected}> before </{name}>", lineno, col))
                    while stack and stack[-1][0] != name:
                        stack.pop()
                    stack.pop()
                else:
                    issues.append(MdxIssue(f"Unexpected closing tag </{name}> with no matching opening tag", lineno, col))
            elif not self_closing:
                stack.append((name, lineno, col))

        # A capitalized tag opener that the full-tag regex couldn't match (e.g. missing ">").
        for m in _BAD_TAG_OPEN_RE.finditer(line):
            if m.start() not in tag_spans:
                issues.append(MdxIssue(f"Malformed tag <{m.group(1)}{m.group(2)}>: missing closing '>'", lineno, m.start() + 1))

    for name, lineno, col in stack:
        issues.append(MdxIssue(f"Expected a closing tag for <{name}>", lineno, col))

    issues.sort(key=lambda i: (i.line, i.column))
    return issues
