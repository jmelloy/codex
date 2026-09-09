/**
 * Shared MDX-compilation logic for any component that needs to turn MDX
 * source into a renderable VNode (MdxViewer.vue for a full block page,
 * MdxBlockRenderer.vue for a single inline block in BlockView.vue).
 */
import { computed, h, type Component } from "vue"
import { compileMdx, MdxCompileError } from "../services/mdxRenderer"
import { resolveLegacyBackedMdxComponent } from "../services/mdxLegacyBlockAdapter"
import Calendar from "../components/blocks/Calendar.vue"
import CodeBlock from "../components/blocks/CodeBlock.vue"

export interface MdxContentContext {
  workspaceId?: string
  notebookId?: string
  parentBlockId?: string
}

// Components with a dedicated MDX-native implementation, resolved before
// falling back to legacy code-fence block components (Weather, GitHub*, etc).
const DEDICATED_COMPONENTS: Record<string, Component> = {
  Calendar,
  CodeBlock,
}

/**
 * Returns a parameterless render function suitable for `<component :is="...">`,
 * so the compiled MDX VNode tree is only recomputed when `content()` (or the
 * resolution context) changes rather than on every parent re-render.
 */
export function useMdxRenderRoot(content: () => string, context: () => MdxContentContext) {
  function resolveComponent(name: string): Component | undefined {
    return DEDICATED_COMPONENTS[name] ?? resolveLegacyBackedMdxComponent(name, context())
  }

  const renderedVNode = computed(() => {
    const source = content()
    if (!source.trim()) {
      return { vnode: null, error: null }
    }
    try {
      return { vnode: compileMdx(source, resolveComponent), error: null }
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
