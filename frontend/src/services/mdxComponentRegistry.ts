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

type PropType = "string" | "number" | "boolean"
interface PropSpec {
  type: PropType
  required?: boolean
}

/** Allowed props per component. Props not listed here (other than `children`) are rejected. */
export const MDX_COMPONENT_PROPS: Record<string, Record<string, PropSpec>> = {
  Calendar: { date: { type: "string" }, start: { type: "string" }, end: { type: "string" } },
  CodeBlock: { language: { type: "string" }, filename: { type: "string" } },
  Weather: { location: { type: "string", required: true }, units: { type: "string" } },
  LinkPreview: { url: { type: "string", required: true } },
  GitHubIssues: {
    owner: { type: "string" },
    repo: { type: "string" },
    state: { type: "string" },
    limit: { type: "number" },
    display: { type: "string" },
  },
  GitHubPulls: {
    owner: { type: "string" },
    repo: { type: "string" },
    state: { type: "string" },
    limit: { type: "number" },
    display: { type: "string" },
  },
  GitHubRepo: { owner: { type: "string" }, repo: { type: "string" }, display: { type: "string" } },
  ApiBlock: {
    url: { type: "string", required: true },
    method: { type: "string" },
    headers: { type: "string" },
    body: { type: "string" },
    refresh: { type: "number" },
    display: { type: "string" },
  },
  DatabaseBlock: {
    query: { type: "string" },
    source: { type: "string" },
    display: { type: "string" },
    properties: { type: "string" },
    limit: { type: "number" },
  },
}

const PASSTHROUGH_PROPS = new Set(["children", "class", "className", "key", "id"])

/**
 * Validate props for a registered component. Returns a list of human-readable
 * problems (empty when valid). Prop values arrive from MDX as strings (JSX
 * expressions are rejected earlier), so number/boolean props accept numeric /
 * "true"|"false" strings.
 */
export function validateComponentProps(
  name: string,
  props: Record<string, unknown> | null | undefined,
): string[] {
  const spec = MDX_COMPONENT_PROPS[name]
  if (!spec) return []
  const given = props ?? {}
  const errors: string[] = []
  for (const [key, def] of Object.entries(spec)) {
    if (def.required && (given[key] === undefined || given[key] === null || given[key] === "")) {
      errors.push(`missing required prop "${key}"`)
    }
  }
  for (const [key, value] of Object.entries(given)) {
    if (PASSTHROUGH_PROPS.has(key)) continue
    const def = spec[key]
    if (!def) {
      errors.push(`unknown prop "${key}"`)
      continue
    }
    if (value === undefined || value === null) continue
    const ok =
      def.type === "string"
        ? typeof value === "string"
        : def.type === "number"
          ? typeof value === "number" ||
            (typeof value === "string" && value.trim() !== "" && !isNaN(Number(value)))
          : typeof value === "boolean" || value === "true" || value === "false"
    if (!ok) errors.push(`prop "${key}" must be a ${def.type}`)
  }
  return errors
}
