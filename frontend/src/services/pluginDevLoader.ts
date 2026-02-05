/**
 * Plugin Dev Loader
 *
 * In dev mode, loads plugin .vue files through Vite's module graph
 * (via import.meta.glob) instead of pre-built .js files. This gives
 * full HMR support and eliminates the need for the plugins-watcher.
 *
 * Only imported in dev mode — tree-shaken from production builds.
 */

import * as yaml from "js-yaml"

// Types shared with pluginLoader.ts
export interface ComponentInfo {
  blockId: string
  blockName: string
  file: string
  icon?: string
  description?: string
}

export interface PluginEntry {
  id: string
  name: string
  version: string
  type: "view" | "theme" | "integration"
  manifest: Record<string, unknown>
  components: Record<string, ComponentInfo>
}

export interface PluginsManifest {
  version: string
  buildTime: string
  plugins: PluginEntry[]
}

export interface FlatComponentEntry {
  pluginId: string
  pluginName: string
  pluginVersion: string
  blockId: string
  blockName: string
  file: string
  icon?: string
  description?: string
}

// Glob all Vue components from plugin directories — Vite resolves these at dev server start
// Each entry is a lazy loader: () => Promise<Module>
const componentGlobs = import.meta.glob<{ default: unknown }>(
  "@plugins/*/components/*.vue",
)

// Glob all manifest YAML files eagerly as raw text
const manifestGlobs = import.meta.glob<string>(
  "@plugins/*/manifest.yml",
  { eager: true, query: "?raw", import: "default" },
)

// Parsed manifest interface (subset of fields we need)
interface ParsedManifest {
  id: string
  name: string
  version: string
  type: "view" | "theme" | "integration"
  description?: string
  blocks?: Array<{
    id: string
    name: string
    component?: string
    description?: string
    icon?: string
  }>
  views?: Array<{
    id: string
    name: string
    description?: string
    icon?: string
    config_schema?: Record<string, unknown>
  }>
  templates?: Array<{
    id: string
    name: string
    description?: string
    icon?: string
  }>
  properties?: Array<{
    name: string
    type: string
    description?: string
    required?: boolean
    secure?: boolean
    enum?: string[]
    default?: unknown
  }>
  theme?: {
    display_name?: string
    category?: string
    className?: string
    stylesheet?: string
  }
  integration?: {
    api_type?: string
    base_url?: string
    auth_method?: string
    rate_limit?: Record<string, unknown>
  }
  endpoints?: Array<{
    id: string
    name: string
    method?: string
    path?: string
    description?: string
    parameters?: Array<Record<string, unknown>>
  }>
}

// Utility functions (matching build.ts)
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

function pascalCase(str: string): string {
  return str.split(/[-_]/).map(capitalize).join("")
}

function kebabCase(str: string): string {
  return str
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .replace(/[\s_]+/g, "-")
    .toLowerCase()
}

// Cache
let devManifestCache: PluginsManifest | null = null
let devComponentLoaders: Map<string, () => Promise<{ default: unknown }>> | null = null
let devFlatComponents: Map<string, FlatComponentEntry> | null = null

/**
 * Extract the plugin directory name from a glob path.
 * Glob keys look like: "../../plugins/weather-api/components/WeatherBlock.vue"
 * or "/absolute/path/plugins/weather-api/components/WeatherBlock.vue"
 * We need the directory name before /components/ or /manifest.yml
 */
function extractPluginDir(globPath: string): string {
  // Match the segment before /components/ or /manifest.yml
  const match = globPath.match(/\/([^/]+)\/(?:components\/|manifest\.yml)/)
  return match?.[1] ?? ""
}

/**
 * Extract the component filename (without .vue) from a glob path.
 */
function extractComponentName(globPath: string): string {
  const match = globPath.match(/\/([^/]+)\.vue$/)
  return match?.[1] ?? ""
}

/**
 * Build component loaders map keyed by blockId.
 *
 * For plugins with blocks in manifest: uses manifest block IDs.
 * For plugins without blocks but with views: maps ViewName.vue -> view-id using kebab-case.
 * For other plugins without blocks: maps ComponentNameBlock.vue -> component-name.
 */
function buildComponentLoaders(): void {
  if (devComponentLoaders) return

  devComponentLoaders = new Map()

  // Parse all manifests first
  const manifests = new Map<string, ParsedManifest>()
  for (const [path, raw] of Object.entries(manifestGlobs)) {
    const dir = extractPluginDir(path)
    if (!dir) continue
    try {
      const parsed = yaml.load(raw) as ParsedManifest
      if (parsed?.id) {
        manifests.set(dir, parsed)
      }
    } catch {
      console.warn(`[pluginDevLoader] Failed to parse manifest: ${path}`)
    }
  }

  // Index all glob loaders by pluginDir -> componentName
  const loadersByPlugin = new Map<string, Map<string, { path: string; loader: () => Promise<{ default: unknown }> }>>()
  for (const [path, loader] of Object.entries(componentGlobs)) {
    const dir = extractPluginDir(path)
    const name = extractComponentName(path)
    if (!dir || !name) continue

    if (!loadersByPlugin.has(dir)) {
      loadersByPlugin.set(dir, new Map())
    }
    loadersByPlugin.get(dir)!.set(name, { path, loader })
  }

  // For each plugin, map blockIds to loaders
  for (const [dir, components] of loadersByPlugin) {
    const manifest = manifests.get(dir)
    if (!manifest) continue

    if (manifest.blocks && manifest.blocks.length > 0) {
      // Plugin has explicit blocks — match block IDs to component files
      for (const block of manifest.blocks) {
        let matched: { path: string; loader: () => Promise<{ default: unknown }> } | undefined

        if (block.component) {
          // Explicit component path: "components/ChartBlock.vue"
          const explicitName = block.component.replace(/^components\//, "").replace(/\.vue$/, "")
          matched = components.get(explicitName)
        }

        if (!matched) {
          // Try common naming conventions (same as build.ts)
          const pascalId = pascalCase(block.id)
          const possibleNames = [
            `${pascalId}Block`,
            pascalId,
            `${capitalize(block.id)}Block`,
            capitalize(block.id),
            block.id,
          ]
          for (const name of possibleNames) {
            if (components.has(name)) {
              matched = components.get(name)
              break
            }
          }
        }

        if (matched) {
          devComponentLoaders.set(block.id, matched.loader)
        }
      }
    }

    // For view plugins, map view IDs to view components
    if (manifest.views && manifest.views.length > 0) {
      for (const view of manifest.views) {
        // Convert view ID to likely component name:
        // "kanban" -> "KanbanView", "task-list" -> "TaskListView"
        const viewComponentName = `${pascalCase(view.id)}View`
        const matched = components.get(viewComponentName)
        if (matched) {
          // Register under the view ID (e.g., "kanban", "task-list")
          devComponentLoaders.set(view.id, matched.loader)
          // Also register the dist-style name for compatibility
          const distName = `${view.id}-view`
          devComponentLoaders.set(distName, matched.loader)
        }
      }
    }

    // For plugins without blocks or views, map all components by kebab-case convention
    if ((!manifest.blocks || manifest.blocks.length === 0) && (!manifest.views || manifest.views.length === 0)) {
      for (const [name, entry] of components) {
        const blockId = kebabCase(name.replace(/Block$/, "").replace(/View$/, ""))
        devComponentLoaders.set(blockId, entry.loader)
      }
    }
  }
}

/**
 * Build the PluginsManifest from glob-loaded manifests.
 * Mirrors the structure that plugins/build.ts generates in plugins.json.
 */
function buildDevManifest(): PluginsManifest {
  if (devManifestCache) return devManifestCache

  // Ensure loaders are built first
  buildComponentLoaders()

  const plugins: PluginEntry[] = []

  // Index component glob paths by pluginDir -> componentName for file path lookup
  const componentPaths = new Map<string, Map<string, string>>()
  for (const path of Object.keys(componentGlobs)) {
    const dir = extractPluginDir(path)
    const name = extractComponentName(path)
    if (!dir || !name) continue
    if (!componentPaths.has(dir)) {
      componentPaths.set(dir, new Map())
    }
    componentPaths.get(dir)!.set(name, path)
  }

  for (const [manifestPath, raw] of Object.entries(manifestGlobs)) {
    const dir = extractPluginDir(manifestPath)
    if (!dir) continue

    let manifest: ParsedManifest
    try {
      manifest = yaml.load(raw) as ParsedManifest
      if (!manifest?.id) continue
    } catch {
      continue
    }

    // Build the manifest object (same structure as build.ts)
    const pluginManifest: Record<string, unknown> = {
      id: manifest.id,
      name: manifest.name,
      version: manifest.version,
      type: manifest.type,
    }

    if (manifest.description) pluginManifest.description = manifest.description
    if (manifest.views?.length) {
      pluginManifest.views = manifest.views.map((v) => ({
        id: v.id,
        name: v.name,
        description: v.description,
        icon: v.icon,
      }))
    }
    if (manifest.templates?.length) {
      pluginManifest.templates = manifest.templates.map((t) => ({
        id: t.id,
        name: t.name,
        description: t.description,
        icon: t.icon,
      }))
    }
    if (manifest.properties?.length) {
      pluginManifest.properties = manifest.properties.map((p) => ({
        name: p.name,
        type: p.type,
        description: p.description,
        required: p.required,
        secure: p.secure,
        enum: p.enum,
        default: p.default,
      }))
    }
    if (manifest.theme) pluginManifest.theme = manifest.theme
    if (manifest.integration) pluginManifest.integration = manifest.integration
    if (manifest.endpoints?.length) {
      pluginManifest.endpoints = manifest.endpoints.map((e) => ({
        id: e.id,
        name: e.name,
        method: e.method,
        path: e.path,
        description: e.description,
        parameters: e.parameters,
      }))
    }
    if (manifest.blocks?.length) {
      pluginManifest.blocks = manifest.blocks.map((b) => ({
        id: b.id,
        name: b.name,
        description: b.description,
        icon: b.icon,
      }))
    }

    // Build components map
    const components: Record<string, ComponentInfo> = {}
    const pluginComponents = componentPaths.get(dir) || new Map()

    if (manifest.blocks && manifest.blocks.length > 0) {
      for (const block of manifest.blocks) {
        // Find which component file this block maps to
        let componentFile = ""
        if (block.component) {
          const explicitName = block.component.replace(/^components\//, "").replace(/\.vue$/, "")
          componentFile = pluginComponents.get(explicitName) || ""
        }
        if (!componentFile) {
          const pascalId = pascalCase(block.id)
          for (const tryName of [`${pascalId}Block`, pascalId, `${capitalize(block.id)}Block`, capitalize(block.id)]) {
            if (pluginComponents.has(tryName)) {
              componentFile = pluginComponents.get(tryName)!
              break
            }
          }
        }

        components[block.id] = {
          blockId: block.id,
          blockName: block.name,
          file: componentFile || `${dir}/components/${pascalCase(block.id)}Block.vue`,
          icon: block.icon,
          description: block.description,
        }
      }
    }

    // Also index view components
    if (manifest.views && manifest.views.length > 0) {
      for (const view of manifest.views) {
        const viewComponentName = `${pascalCase(view.id)}View`
        const componentFile = pluginComponents.get(viewComponentName)
        if (componentFile) {
          components[view.id] = {
            blockId: view.id,
            blockName: view.name,
            file: componentFile,
            icon: view.icon,
            description: view.description,
          }
        }
      }
    }

    plugins.push({
      id: manifest.id,
      name: manifest.name,
      version: manifest.version,
      type: manifest.type,
      manifest: pluginManifest,
      components,
    })
  }

  devManifestCache = {
    version: "1.0.0-dev",
    buildTime: new Date().toISOString(),
    plugins,
  }

  return devManifestCache
}

/**
 * Get the dev manifest (same shape as plugins.json).
 */
export function getDevManifest(): PluginsManifest {
  return buildDevManifest()
}

/**
 * Get a component loader function for a given blockId/viewId.
 * Returns the glob loader, or undefined if not found.
 */
export function getDevComponentLoader(
  blockId: string,
): (() => Promise<{ default: unknown }>) | undefined {
  buildComponentLoaders()
  return devComponentLoaders!.get(blockId)
}

/**
 * Check if a dev component exists for a given blockId/viewId.
 */
export function hasDevComponent(blockId: string): boolean {
  buildComponentLoaders()
  return devComponentLoaders!.has(blockId)
}

/**
 * Get the flattened components map (same shape as pluginLoader's getComponentsMap).
 */
export function getDevFlatComponents(): Map<string, FlatComponentEntry> {
  if (devFlatComponents) return devFlatComponents

  const manifest = buildDevManifest()
  devFlatComponents = new Map()

  for (const plugin of manifest.plugins) {
    for (const [blockId, comp] of Object.entries(plugin.components)) {
      devFlatComponents.set(blockId, {
        pluginId: plugin.id,
        pluginName: plugin.name,
        pluginVersion: plugin.version,
        blockId: comp.blockId,
        blockName: comp.blockName,
        file: comp.file,
        icon: comp.icon,
        description: comp.description,
      })
    }
  }

  return devFlatComponents
}
