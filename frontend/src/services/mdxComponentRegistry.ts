/**
 * MDX component registry — frontend mirror of codex.core.mdx.MDX_COMPONENT_REGISTRY.
 *
 * This is the enforcement point: mdxRenderer.ts refuses to resolve a component
 * that isn't listed here and renders a placeholder instead.
 */
export const MDX_COMPONENT_REGISTRY: Record<string, string> = {
  Calendar: "Displays a date or date range on a calendar",
  CodeBlock: "Syntax-highlighted code with an optional filename/language",
  Weather: "Current weather and forecast for a location",
  LinkPreview: "Unfurled preview card for a URL",
  GitHubIssues: "List of issues from a GitHub repository",
  GitHubPulls: "List of pull requests from a GitHub repository",
  GitHubRepo: "GitHub repository summary card",
  ApiBlock: "Fetch and display data from a REST API endpoint",
  DatabaseBlock: "Query the notebook database and display results",
}

export const ALLOWED_COMPONENT_NAMES: Set<string> = new Set(Object.keys(MDX_COMPONENT_REGISTRY))

// Matches capitalized JSX-style tags, e.g. `<Calendar` or `</Calendar>` — mirrors
// codex.core.mdx._COMPONENT_TAG_RE.
const COMPONENT_TAG_RE = /<\/?([A-Z][A-Za-z0-9]*)\b/g

/** Return the set of capitalized JSX-style component tags referenced in MDX source. */
export function extractComponentNames(mdxSource: string): Set<string> {
  const names = new Set<string>()
  for (const match of mdxSource.matchAll(COMPONENT_TAG_RE)) {
    names.add(match[1])
  }
  return names
}
