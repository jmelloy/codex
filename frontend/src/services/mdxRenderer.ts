/**
 * MDX -> Vue rendering.
 *
 * @mdx-js/mdx is renderer-agnostic: it compiles MDX to a JS module that calls
 * a `jsx`/`jsxs`/`Fragment` triplet you supply (the same "pragma" mechanism
 * React/Preact/etc plug into). We supply implementations backed by Vue's
 * `h()` instead, so the compiled MDXContent() function produces real Vue
 * VNodes directly - no React runtime involved.
 *
 * Security model: every capitalized JSX tag referenced in the MDX source
 * *must* be present in the `components` map passed to MDXContent, or the
 * compiled code throws (`_missingMdxReference`) before anything renders. We
 * pre-populate that map for every component name found in the source -
 * known ones (see mdxComponentRegistry.ts) resolve to their real Vue
 * component, unknown ones resolve to a visible "unauthorized" placeholder -
 * mirroring the backend's allowlist in codex.core.mdx.
 *
 * Legacy (plain Markdown) content goes through the same pipeline with
 * `format: "md"`, which parses CommonMark only: raw HTML, JSX and `{...}`
 * expressions are dropped or kept as literal text, so it needs no allowlist.
 */
import { Fragment as VueFragment, h, type Component, type VNode, type VNodeChild } from "vue"
import { evaluateSync } from "@mdx-js/mdx"
import remarkBreaks from "remark-breaks"
import remarkGfm from "remark-gfm"
import {
  ALLOWED_COMPONENT_NAMES,
  extractComponentNames,
  validateComponentProps,
} from "./mdxComponentRegistry"

// hast-util-to-jsx-runtime (used internally by @mdx-js/mdx) emits React-style
// attribute names for host HTML elements regardless of which jsx runtime is
// plugged in - translate the handful that differ from the DOM/Vue attribute.
const REACT_ATTR_ALIASES: Record<string, string> = {
  className: "class",
  htmlFor: "for",
}

function translateHostProps(props: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(props)) {
    out[REACT_ATTR_ALIASES[key] ?? key] = value
  }
  return out
}

/** Recursively flatten JSX/MDX children into plain text (used by components like CodeBlock that need raw text, not a slot tree). */
export function flattenChildrenToText(node: unknown): string {
  if (node === null || node === undefined || typeof node === "boolean") return ""
  if (typeof node === "string" || typeof node === "number") return String(node)
  if (Array.isArray(node)) return node.map(flattenChildrenToText).join("")
  if (typeof node === "object" && "children" in (node as Record<string, unknown>)) {
    return flattenChildrenToText((node as { children: unknown }).children)
  }
  return ""
}

function createUnauthorizedComponent(name: string): Component {
  return {
    name: `MdxUnauthorized_${name}`,
    setup() {
      return () =>
        h("div", { class: "mdx-unauthorized-component" }, [
          h("span", { class: "mdx-unauthorized-icon" }, "⚠️"),
          h("span", {}, `Component "${name}" is not authorized and was not rendered.`),
        ])
    },
  }
}

const invalidPropsCache = new Map<string, Component>()

/** Placeholder for invalid props, cached per component name + error set so the VNode type stays stable across renders. */
function createInvalidPropsComponent(name: string, errors: string[]): Component {
  const key = `${name}\u0000${errors.join("\u0000")}`
  const cached = invalidPropsCache.get(key)
  if (cached) return cached
  const component: Component = {
    name: `MdxInvalidProps_${name}`,
    setup() {
      return () =>
        h("div", { class: "mdx-unauthorized-component mdx-invalid-props" }, [
          h("span", { class: "mdx-unauthorized-icon" }, "⚠️"),
          h("span", {}, `<${name}> has invalid props: ${errors.join("; ")}.`),
        ])
    },
  }
  invalidPropsCache.set(key, component)
  return component
}

/** Wrap a real component so its props are validated before every render; invalid props render an error placeholder instead. */
const validatedCache = new WeakMap<object, Component>()

function withPropValidation(name: string, inner: Component): Component {
  // Cached per component so recompiles don't hand Vue a new type (which would remount it).
  const cached = validatedCache.get(inner)
  if (cached) return cached
  const wrapped = {
    name: `MdxValidated_${name}`,
    inheritAttrs: false,
    setup(_props, { attrs, slots }) {
      return () => {
        const errors = validateComponentProps(name, attrs)
        if (errors.length) return h(createInvalidPropsComponent(name, errors))
        return h(inner as any, attrs, slots)
      }
    },
  } as Component
  validatedCache.set(inner, wrapped)
  return wrapped
}

/** Build the `components` map MDXContent() needs: real components for allowlisted names, a visible placeholder for anything else. */
export function buildComponentsMap(
  mdxSource: string,
  resolve: (name: string) => Component | undefined,
): Record<string, Component> {
  const map: Record<string, Component> = {}
  for (const name of extractComponentNames(mdxSource)) {
    const resolved = ALLOWED_COMPONENT_NAMES.has(name) ? resolve(name) : undefined
    map[name] = resolved ? withPropValidation(name, resolved) : createUnauthorizedComponent(name)
  }
  return map
}

export type MdxFormat = "mdx" | "md"

// mdast/hast node types @mdx-js/mdx emits for ESM (`import`/`export`) and JS
// expressions (`{...}`) - see mdast-util-mdxjs-esm and mdast-util-mdx-expression.
// These let MDX source run arbitrary JS, which the allowed-component model
// doesn't gate at all, so they're rejected outright before evaluation.
const DISALLOWED_MDX_JS_NODE_TYPES = new Set(["mdxjsEsm", "mdxFlowExpression", "mdxTextExpression"])

// Literal lowercase JSX (`<a href=...>`) becomes a real DOM element, so it can't
// carry script: no script-bearing tags, no `on*` handlers, no script URLs.
const DISALLOWED_HOST_TAGS = new Set([
  "script",
  "style",
  "iframe",
  "object",
  "embed",
  "form",
  "base",
  "meta",
  "link",
])
const SCRIPT_URL_RE = /^\s*(javascript:|vbscript:|data:(?!image\/))/i

/** Whether `url` would run script if used as a link target. */
export function isScriptUrl(url: string): boolean {
  return SCRIPT_URL_RE.test(url)
}

function assertSafeHostElement(name: string, attributes: Record<string, unknown>[]): void {
  if (DISALLOWED_HOST_TAGS.has(name.toLowerCase())) {
    throw new Error(`MDX content may not contain <${name}> elements`)
  }
  for (const attr of attributes) {
    const attrName = String(attr.name ?? "")
    if (/^on/i.test(attrName)) {
      throw new Error(
        `MDX element <${name}> may not have an event handler attribute ("${attrName}")`,
      )
    }
    if (typeof attr.value === "string" && SCRIPT_URL_RE.test(attr.value)) {
      throw new Error(
        `MDX element <${name}> attribute "${attrName}" may not be a script or data URL`,
      )
    }
  }
}

/** Throws if `tree` contains ESM, a bare JS expression, a JSX attribute driven by one (mdast-util-mdx-jsx's `mdxJsxExpressionAttribute` / `mdxJsxAttributeValueExpression`), or an unsafe host element. */
function assertNoMdxJsNodes(node: unknown): void {
  if (!node || typeof node !== "object") return
  const n = node as Record<string, unknown>
  if (typeof n.type === "string" && DISALLOWED_MDX_JS_NODE_TYPES.has(n.type)) {
    throw new Error(
      `MDX content may not contain JS expressions or import/export statements (found "${n.type}")`,
    )
  }
  if (
    (n.type === "mdxJsxFlowElement" || n.type === "mdxJsxTextElement") &&
    Array.isArray(n.attributes)
  ) {
    for (const attr of n.attributes as Record<string, unknown>[]) {
      const value = attr.value as Record<string, unknown> | string | undefined
      if (
        attr.type === "mdxJsxExpressionAttribute" ||
        (value !== null &&
          typeof value === "object" &&
          value.type === "mdxJsxAttributeValueExpression")
      ) {
        throw new Error(
          `MDX component attribute "${attr.name}" on <${n.name}> may not be a JS expression`,
        )
      }
    }
    if (typeof n.name === "string" && /^[a-z]/.test(n.name)) {
      assertSafeHostElement(n.name, n.attributes as Record<string, unknown>[])
    }
  }
  if (Array.isArray(n.children)) {
    for (const child of n.children) assertNoMdxJsNodes(child)
  }
}

/** remark plugin: reject MDX ESM/expression nodes before they reach recma/evaluateSync. */
function remarkRejectMdxJs() {
  return (tree: unknown) => {
    assertNoMdxJsNodes(tree)
  }
}

function renderNode(type: unknown, rawProps: Record<string, unknown> | null | undefined): VNode {
  const { children, ...rest } = rawProps ?? {}
  const childVNodes = (children ?? undefined) as VNodeChild
  if (type === VueFragment) {
    return h(VueFragment as any, null, childVNodes as any)
  }
  const props = typeof type === "string" ? translateHostProps(rest) : rest
  return h(type as any, props, childVNodes as any)
}

/** Compile and evaluate MDX (or plain Markdown, with `format: "md"`) into a single Vue VNode tree, ready to render. */
export function renderMdxToVNode(
  mdxSource: string,
  components: Record<string, Component>,
  format: MdxFormat = "mdx",
): VNode {
  const { default: MDXContent } = evaluateSync(mdxSource, {
    Fragment: VueFragment,
    jsx: (type: unknown, props: Record<string, unknown> | null) => renderNode(type, props),
    jsxs: (type: unknown, props: Record<string, unknown> | null) => renderNode(type, props),
    format,
    // Legacy Markdown was rendered with single newlines as line breaks; keep that.
    remarkPlugins: format === "md" ? [remarkGfm, remarkBreaks] : [remarkGfm, remarkRejectMdxJs],
  }) as { default: (props: Record<string, unknown>) => VNode }

  return MDXContent({ components })
}

export class MdxCompileError extends Error {
  line?: number
  column?: number

  constructor(message: string, position?: { line?: number; column?: number }) {
    super(message)
    this.name = "MdxCompileError"
    this.line = position?.line
    this.column = position?.column
  }
}

/** Turn a raw @mdx-js/mdx (VFileMessage) failure into a short, user-friendly MdxCompileError. */
export function toMdxCompileError(e: unknown): MdxCompileError {
  if (e instanceof MdxCompileError) return e
  type Pos = { line?: number | null; column?: number | null }
  const err = (e ?? {}) as {
    reason?: string
    message?: string
    place?: (Pos & { start?: Pos }) | null
  } & Pos
  // VFileMessage exposes the position as `line`/`column` and as `place` (a point or a {start,end} range).
  const raw = String(err.reason ?? err.message ?? e)
  let pos: Pos = err.place?.start ?? err.place ?? err
  if (!pos.line) {
    // Some errors only carry the position inside the reason, e.g. "... (3:1-3:11)".
    const m = /\((\d+):(\d+)(?:-\d+:\d+)?\)\s*$/.exec(raw)
    if (m) pos = { line: Number(m[1]), column: Number(m[2]) }
  }
  let message = raw
  if (/Unexpected closing slash/.test(raw))
    message = `${raw} (a closing tag has no matching opening tag)`
  else if (/Expected a closing tag/.test(raw))
    message = `${raw} (every JSX tag must be closed, e.g. <Calendar />)`
  else if (/Could not parse expression/.test(raw))
    message = `${raw} (curly braces start a JS expression - escape literal braces as \\{ )`
  else if (/Unexpected character `<`/.test(raw))
    message = `${raw} (escape a literal "<" as \\< or &lt;)`
  return new MdxCompileError(message, {
    line: pos.line ?? undefined,
    column: pos.column ?? undefined,
  })
}

/**
 * Compile MDX source to a Vue VNode, resolving component tags via `resolve`.
 * `hostOverrides` replace markdown-generated elements (`a`, `img`, `pre`, ...).
 * Throws MdxCompileError on invalid MDX.
 */
export function compileMdx(
  mdxSource: string,
  resolve: (name: string) => Component | undefined,
  {
    format = "mdx",
    hostOverrides = {},
  }: { format?: MdxFormat; hostOverrides?: Record<string, Component> } = {},
): VNode {
  const components = {
    ...hostOverrides,
    ...(format === "mdx" ? buildComponentsMap(mdxSource, resolve) : {}),
  }
  try {
    return renderMdxToVNode(mdxSource, components, format)
  } catch (e) {
    throw toMdxCompileError(e)
  }
}
