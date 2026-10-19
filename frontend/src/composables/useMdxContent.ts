/**
 * Shared MDX-compilation logic for any component that needs to turn block
 * content into a renderable VNode (MdxViewer.vue for a full block page,
 * MdxBlockRenderer.vue for a single inline block in BlockView.vue). Legacy
 * Markdown blocks render through the same pipeline with `format: "md"`.
 */
import { computed, defineComponent, h, ref, type Component, type VNode } from "vue"
import {
  compileMdx,
  flattenChildrenToText,
  isScriptUrl,
  MdxCompileError,
  type MdxFormat,
} from "../services/mdxRenderer"
import {
  renderLegacyBlock,
  resolveLegacyBackedMdxComponent,
  type MdxBlockContext,
} from "../services/mdxLegacyBlockAdapter"
import { getAvailableBlockTypes, isBlockTypeKnown } from "../services/pluginLoader"
import { isLocalFileReference, resolveFileUrl } from "../utils/markdownHelpers"
import { parseBlockConfig } from "../utils/blockConfig"
import Calendar from "../components/blocks/Calendar.vue"
import CodeBlock from "../components/blocks/CodeBlock.vue"

export type MdxContentContext = MdxBlockContext

// Components with a dedicated MDX-native implementation, resolved before
// falling back to legacy code-fence block components (Weather, GitHub*, etc).
const DEDICATED_COMPONENTS: Record<string, Component> = {
  Calendar,
  CodeBlock,
}

// Flips once the plugin manifest has loaded, so fences for plugin block types
// (e.g. ```link-preview) re-render once it's known whether they're plugins.
const pluginManifestLoaded = ref(false)

/**
 * Overrides for markdown-generated elements: local links/images resolve to the
 * notebook's content API, script URLs are dropped, and fenced code either
 * renders a plugin block (```weather) or syntax-highlighted code.
 */
function createHostOverrides(context: () => MdxContentContext): Record<string, Component> {
  const MdxLink = defineComponent({
    name: "MdxLink",
    inheritAttrs: false,
    setup(_props, { attrs, slots }) {
      return () => {
        const href = String(attrs.href ?? "")
        if (!href || isScriptUrl(href)) return h("span", slots.default?.())
        if (!isLocalFileReference(href)) {
          return h("a", { ...attrs, target: "_blank", rel: "noopener" }, slots.default?.())
        }
        const { workspaceId, notebookId } = context()
        const resolved = resolveFileUrl(href, workspaceId, notebookId)
        // BlockView intercepts clicks on data-internal-link anchors to navigate in-app.
        return h("a", { ...attrs, href: resolved, "data-internal-link": href }, slots.default?.())
      }
    },
  })

  const MdxImage = defineComponent({
    name: "MdxImage",
    inheritAttrs: false,
    setup(_props, { attrs }) {
      return () => {
        const src = String(attrs.src ?? "")
        const { workspaceId, notebookId } = context()
        return h("img", { ...attrs, src: resolveFileUrl(src, workspaceId, notebookId) })
      }
    },
  })

  const MdxFencedCode = defineComponent({
    name: "MdxFencedCode",
    inheritAttrs: false,
    setup(_props, { slots }) {
      return () => {
        const code = slots.default?.()[0] as VNode | undefined
        const className = String((code?.props as Record<string, unknown> | null)?.class ?? "")
        const language = className.match(/language-([-\w]+)/)?.[1]
        const text = flattenChildrenToText(code).replace(/\n$/, "")

        if (language) {
          const known = isBlockTypeKnown(language)
          if (known === undefined && !pluginManifestLoaded.value) {
            getAvailableBlockTypes().finally(() => (pluginManifestLoaded.value = true))
            return null
          }
          if (known) return renderLegacyBlock(language, parseBlockConfig(text), context())
        }
        return h(CodeBlock, { language, mdxChildren: text })
      }
    },
  })

  return { a: MdxLink, img: MdxImage, pre: MdxFencedCode }
}

/**
 * Returns a parameterless render function suitable for `<component :is="...">`,
 * so the compiled MDX VNode tree is only recomputed when `content()`, `format()`
 * (or the resolution context) changes rather than on every parent re-render.
 */
export function useMdxRenderRoot(
  content: () => string,
  context: () => MdxContentContext,
  format: () => MdxFormat = () => "mdx",
) {
  // Built once per instance so recompiling doesn't hand Vue new component
  // types (which would remount every embedded block on each edit).
  const hostOverrides = createHostOverrides(context)
  const resolvedComponents = new Map<string, Component | undefined>()
  function resolveComponent(name: string): Component | undefined {
    if (!resolvedComponents.has(name)) {
      resolvedComponents.set(
        name,
        DEDICATED_COMPONENTS[name] ?? resolveLegacyBackedMdxComponent(name, context),
      )
    }
    return resolvedComponents.get(name)
  }

  const renderedVNode = computed(() => {
    const source = content()
    if (!source.trim()) {
      return { vnode: null, error: null }
    }
    try {
      return {
        vnode: compileMdx(source, resolveComponent, { format: format(), hostOverrides }),
        error: null,
      }
    } catch (e) {
      const message = e instanceof MdxCompileError ? e.message : String(e)
      console.error("MDX compile error:", e)
      return { vnode: null, error: message }
    }
  })

  return () => {
    const { vnode, error } = renderedVNode.value
    if (error) {
      return h("p", { class: "error-content" }, `Error rendering MDX: ${error}`)
    }
    if (!vnode) {
      return h("p", { class: "empty-content" }, "No content to display")
    }
    return vnode
  }
}
