/**
 * Adapts the existing code-fence block components (WeatherBlock.vue,
 * ApiBlock.vue, DatabaseBlock.vue, GitHub*Block.vue, link-preview plugin,
 * etc.) for use as MDX components.
 *
 * Those components were built for the legacy ` ```weather\nlocation: NYC\n``` `
 * code-fence syntax and expect their settings nested under a `config` prop.
 * MDX instead gives each attribute as its own flat prop, e.g.
 * `<Weather location="NYC" />` -> `{ location: "NYC" }`. This wraps a
 * legacy block component so it can be resolved for either syntax without
 * changing the legacy components themselves.
 */
import { defineComponent, h, type Component } from "vue"
import { loadPluginComponent } from "./pluginLoader"

export interface MdxBlockContext {
  workspaceId?: string
  notebookId?: string
  parentBlockId?: string
}

/** Wrap a legacy `blockType` (as known to pluginLoader.loadPluginComponent) for use as an MDX component. */
export function wrapLegacyBlockForMdx(blockType: string, context: MdxBlockContext): Component {
  const inner = loadPluginComponent(blockType)
  return defineComponent({
    name: `MdxLegacyAdapter_${blockType}`,
    inheritAttrs: false,
    setup(_props, { attrs }) {
      return () =>
        h(inner, {
          config: { ...attrs },
          workspaceId: context.workspaceId,
          notebookId: context.notebookId,
          parentBlockId: context.parentBlockId,
        })
    },
  })
}

// Maps MDX component names (codex.core.mdx.MDX_COMPONENT_REGISTRY) to the
// pluginLoader block-type key that renders them.
const MDX_NAME_TO_LEGACY_BLOCK_TYPE: Record<string, string> = {
  Weather: "weather",
  LinkPreview: "link-preview",
  GitHubIssues: "github-issues",
  GitHubPulls: "github-pulls",
  GitHubRepo: "github-repo",
  ApiBlock: "api",
  DatabaseBlock: "database",
}

/** Resolve an MDX component name backed by a legacy block component, or undefined if it has a dedicated MDX component instead (Calendar, CodeBlock). */
export function resolveLegacyBackedMdxComponent(
  name: string,
  context: MdxBlockContext,
): Component | undefined {
  const blockType = MDX_NAME_TO_LEGACY_BLOCK_TYPE[name]
  return blockType ? wrapLegacyBlockForMdx(blockType, context) : undefined
}
