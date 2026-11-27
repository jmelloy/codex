/**
 * Prop validation for MDX components. MDX attributes are always strings (JS
 * expression attributes are rejected by mdxRenderer), so every spec parses
 * from a string. validateProps() runs before a component renders; on failure
 * the wrapper in mdxSafeComponent.ts shows the errors instead of the component.
 */
export type PropType = "string" | "number" | "boolean" | "json" | "url" | "enum"

export interface PropSpec {
  type: PropType
  required?: boolean
  default?: unknown
  min?: number
  max?: number
  maxLength?: number
  values?: readonly string[]
  description?: string
}

export type PropSchema = Record<string, PropSpec>

export interface ValidationResult {
  valid: boolean
  props: Record<string, unknown>
  errors: string[]
}

const MAX_JSON_LENGTH = 100_000
const ALLOWED_URL_PROTOCOLS = new Set(["http:", "https:"])

/** Whether `value` is an absolute http(s) URL or a same-origin path ("/..."). */
export function isSafeUrl(value: string): boolean {
  if (value.startsWith("/") && !value.startsWith("//")) return true
  try {
    return ALLOWED_URL_PROTOCOLS.has(new URL(value).protocol)
  } catch {
    return false
  }
}

function coerce(name: string, spec: PropSpec, raw: unknown): { value?: unknown; error?: string } {
  switch (spec.type) {
    case "string": {
      const s = String(raw)
      if (spec.maxLength !== undefined && s.length > spec.maxLength) {
        return { error: `"${name}" exceeds ${spec.maxLength} characters` }
      }
      return { value: s }
    }
    case "number": {
      const n = typeof raw === "number" ? raw : Number(String(raw).trim())
      if (String(raw).trim() === "" || !Number.isFinite(n)) return { error: `"${name}" must be a number` }
      if (spec.min !== undefined && n < spec.min) return { error: `"${name}" must be >= ${spec.min}` }
      if (spec.max !== undefined && n > spec.max) return { error: `"${name}" must be <= ${spec.max}` }
      return { value: n }
    }
    case "boolean": {
      if (typeof raw === "boolean") return { value: raw }
      // Bare attribute (`<X flag />`) arrives as true.
      const s = String(raw).toLowerCase()
      if (s === "true" || s === "") return { value: true }
      if (s === "false") return { value: false }
      return { error: `"${name}" must be true or false` }
    }
    case "enum": {
      const s = String(raw)
      if (!spec.values?.includes(s)) return { error: `"${name}" must be one of: ${spec.values?.join(", ")}` }
      return { value: s }
    }
    case "url": {
      const s = String(raw).trim()
      if (!isSafeUrl(s)) return { error: `"${name}" must be an http(s) URL or a site-relative path` }
      return { value: s }
    }
    case "json": {
      if (typeof raw !== "string") return { value: raw }
      if (raw.length > MAX_JSON_LENGTH) return { error: `"${name}" is too large` }
      try {
        return { value: JSON.parse(raw) }
      } catch {
        return { error: `"${name}" must be valid JSON` }
      }
    }
  }
}

/** Validate and coerce raw MDX attributes against `schema`. Unknown props are errors. */
export function validateProps(schema: PropSchema, raw: Record<string, unknown>): ValidationResult {
  const errors: string[] = []
  const props: Record<string, unknown> = {}

  for (const key of Object.keys(raw)) {
    if (key === "children" || key === "class" || key === "key") continue
    if (!(key in schema)) errors.push(`Unknown prop "${key}"`)
  }

  for (const [name, spec] of Object.entries(schema)) {
    const value = raw[name]
    if (value === undefined || value === null) {
      if (spec.required) errors.push(`Missing required prop "${name}"`)
      else if (spec.default !== undefined) props[name] = spec.default
      continue
    }
    const result = coerce(name, spec, value)
    if (result.error) errors.push(result.error)
    else props[name] = result.value
  }

  return { valid: errors.length === 0, props, errors }
}
