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
 */
import { Fragment as VueFragment, h, type Component, type VNode, type VNodeChild } from "vue"
import { evaluateSync } from "@mdx-js/mdx"
import { ALLOWED_COMPONENT_NAMES, extractComponentNames } from "./mdxComponentRegistry"

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

/** Build the `components` map MDXContent() needs: real components for allowlisted names, a visible placeholder for anything else. */
export function buildComponentsMap(
  mdxSource: string,
  resolve: (name: string) => Component | undefined,
): Record<string, Component> {
  const map: Record<string, Component> = {}
  for (const name of extractComponentNames(mdxSource)) {
    const resolved = ALLOWED_COMPONENT_NAMES.has(name) ? resolve(name) : undefined
    map[name] = resolved ?? createUnauthorizedComponent(name)
  }
  return map
}

// mdast/hast node types @mdx-js/mdx emits for ESM (`import`/`export`) and JS
// expressions (`{...}`) - see mdast-util-mdxjs-esm and mdast-util-mdx-expression.
// These let MDX source run arbitrary JS, which the allowed-component model
// doesn't gate at all, so they're rejected outright before evaluation.
const DISALLOWED_MDX_JS_NODE_TYPES = new Set(["mdxjsEsm", "mdxFlowExpression", "mdxTextExpression"])

/** Throws if `tree` contains ESM, a bare JS expression, or a JSX attribute driven by one (mdast-util-mdx-jsx's `mdxJsxExpressionAttribute` / `mdxJsxAttributeValueExpression`). */
function assertNoMdxJsNodes(node: unknown): void {
  if (!node || typeof node !== "object") return
  const n = node as Record<string, unknown>
  if (typeof n.type === "string" && DISALLOWED_MDX_JS_NODE_TYPES.has(n.type)) {
    throw new Error(`MDX content may not contain JS expressions or import/export statements (found "${n.type}")`)
  }
  if ((n.type === "mdxJsxFlowElement" || n.type === "mdxJsxTextElement") && Array.isArray(n.attributes)) {
    for (const attr of n.attributes as Record<string, unknown>[]) {
      const value = attr.value as Record<string, unknown> | string | undefined
      if (
        attr.type === "mdxJsxExpressionAttribute" ||
        (value !== null && typeof value === "object" && value.type === "mdxJsxAttributeValueExpression")
      ) {
        throw new Error(
          `MDX component attribute "${attr.name}" on <${n.name}> may not be a JS expression`,
        )
      }
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

/** Compile and evaluate MDX source into a single Vue VNode tree, ready to render. */
export function renderMdxToVNode(mdxSource: string, components: Record<string, Component>): VNode {
  const { default: MDXContent } = evaluateSync(mdxSource, {
    Fragment: VueFragment,
    jsx: (type: unknown, props: Record<string, unknown> | null) => renderNode(type, props),
    jsxs: (type: unknown, props: Record<string, unknown> | null) => renderNode(type, props),
    remarkPlugins: [remarkRejectMdxJs],
  }) as { default: (props: Record<string, unknown>) => VNode }

  return MDXContent({ components })
}

export class MdxCompileError extends Error {}

/** Compile MDX source to a Vue VNode, resolving component tags via `resolve`. Throws MdxCompileError on invalid MDX. */
export function compileMdx(
  mdxSource: string,
  resolve: (name: string) => Component | undefined,
): VNode {
  const components = buildComponentsMap(mdxSource, resolve)
  try {
    return renderMdxToVNode(mdxSource, components)
  } catch (e) {
    throw new MdxCompileError(e instanceof Error ? e.message : String(e))
  }
}
