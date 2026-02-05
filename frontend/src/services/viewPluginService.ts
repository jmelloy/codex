/**
 * View Plugin Service
 *
 * Manages dynamic loading of view components from the plugin system.
 * View components are built by the plugin build script (plugins/build.ts)
 * and output to plugins/{plugin}/dist/{view}.js
 */

import { defineAsyncComponent, h, type Component } from "vue"
import { getAvailableViews } from "./pluginLoader"

export interface ViewPlugin {
  id: string
  name: string
  description: string
  icon?: string
  plugin_id: string
  plugin_name: string
  config_schema?: Record<string, any>
}

// Map view types to their source paths for development fallback
const VIEW_FALLBACK_PATHS: Record<string, string> = {
  kanban: "tasks/components/KanbanView.vue",
  "task-list": "tasks/components/TaskListView.vue",
  rollup: "rollup/components/RollupView.vue",
  gallery: "gallery/components/GalleryView.vue",
  corkboard: "corkboard/components/CorkboardView.vue",
}

// Map view types to their expected component names in dist/
const VIEW_DIST_NAMES: Record<string, string> = {
  kanban: "kanban-view",
  "task-list": "task-list-view",
  rollup: "rollup-view",
  gallery: "gallery-view",
  corkboard: "corkboard-view",
}

// Base path for plugins
const PLUGINS_BASE = "/plugins"

/**
 * Create a fallback component for when view plugins fail to load
 */
function createFallbackComponent(viewType: string, error?: string): Component {
  return {
    props: ["data", "config", "definition", "workspaceId"] as const,
    setup() {
      return () =>
        h("div", { class: "view-fallback p-6 bg-yellow-50 border border-yellow-200 rounded-lg" }, [
          h("h3", { class: "text-yellow-800 font-semibold mb-2" }, `${viewType} View`),
          h("p", { class: "text-yellow-600" },
            error || "View component not available. Run 'npm run build' in the plugins directory."
          ),
        ])
    },
  }
}

/**
 * Create a loading component
 */
const LoadingComponent: Component = {
  setup() {
    return () =>
      h("div", { class: "flex items-center justify-center h-64" }, [
        h("div", { class: "text-text-tertiary" }, "Loading view..."),
      ])
  },
}

class ViewPluginService {
  private availableViews: Map<string, ViewPlugin> = new Map()
  private initialized = false
  private initPromise: Promise<void> | null = null

  /**
   * Initialize the view plugin service by loading available views from plugins
   */
  async initialize(): Promise<void> {
    if (this.initPromise) {
      return this.initPromise
    }

    if (this.initialized) {
      return
    }

    this.initPromise = this._doInitialize()

    try {
      await this.initPromise
    } finally {
      this.initPromise = null
    }
  }

  private async _doInitialize(): Promise<void> {
    try {
      const views = await getAvailableViews()

      for (const view of views) {
        this.availableViews.set(view.id, {
          id: view.id,
          name: view.name,
          description: view.description,
          icon: view.icon,
          plugin_id: view.pluginId,
          plugin_name: view.pluginName,
        })
      }

      this.initialized = true
    } catch (error) {
      console.error("Failed to load available views from plugins:", error)
      this.initialized = true
    }
  }

  /**
   * Get all available views
   */
  getAvailableViews(): ViewPlugin[] {
    return Array.from(this.availableViews.values())
  }

  /**
   * Get a specific view by ID
   */
  getView(viewId: string): ViewPlugin | undefined {
    return this.availableViews.get(viewId)
  }

  /**
   * Check if a view type is available
   */
  isViewAvailable(viewId: string): boolean {
    return this.availableViews.has(viewId)
  }

  /**
   * Get the valid view type IDs
   */
  getValidViewTypes(): string[] {
    return Array.from(this.availableViews.keys())
  }

  /**
   * Load a view component dynamically
   * In dev mode, uses glob loader for HMR. Otherwise tries compiled dist/ first.
   */
  async loadViewComponent(viewId: string): Promise<Component> {
    // Dashboard is loaded from frontend (has frontend service dependencies)
    if (viewId === "dashboard") {
      const module = await import("@/components/views/DashboardView.vue")
      return module.default
    }

    // In dev mode, use glob loader for full HMR support
    if (import.meta.env.DEV) {
      try {
        const { getDevComponentLoader } = await import("./pluginDevLoader")
        const loader = getDevComponentLoader(viewId)
        if (loader) {
          const module = await loader()
          return (module.default || module) as Component
        }
      } catch (err) {
        console.warn(`[dev] Failed to load view component via glob for ${viewId}:`, err)
      }
    }

    // Production path: try to load from dist/ first
    const distName = VIEW_DIST_NAMES[viewId] || `${viewId}-view`
    try {
      const moduleUrl = `${PLUGINS_BASE}/${this.getPluginIdForView(viewId)}/dist/${distName}.js`
      const module = await import(/* @vite-ignore */ moduleUrl)
      return module.default || module
    } catch (err) {
      console.warn(`Failed to load compiled view component for ${viewId}:`, err)
    }

    // Fallback: try to load from source files (for development without build)
    const fallbackPath = VIEW_FALLBACK_PATHS[viewId]
    if (fallbackPath) {
      try {
        const module = await import(/* @vite-ignore */ `${PLUGINS_BASE}/${fallbackPath}`)
        return module.default || module
      } catch (err) {
        console.warn(`Failed to load fallback view component for ${viewId}:`, err)
      }
    }

    // Return fallback component
    return createFallbackComponent(viewId)
  }

  /**
   * Get the plugin ID for a view
   */
  private getPluginIdForView(viewId: string): string {
    const view = this.availableViews.get(viewId)
    if (view) {
      return view.plugin_id
    }
    // Fallback mapping for common views
    const viewToPlugin: Record<string, string> = {
      kanban: "tasks",
      "task-list": "tasks",
      rollup: "rollup",
      gallery: "gallery",
      corkboard: "corkboard",
      dashboard: "core",
    }
    return viewToPlugin[viewId] || viewId
  }

  /**
   * Get an async component wrapper for a view type
   */
  getViewComponent(viewId: string): Component {
    // Dashboard is loaded from frontend
    if (viewId === "dashboard") {
      return defineAsyncComponent({
        loader: () => import("@/components/views/DashboardView.vue"),
        loadingComponent: LoadingComponent,
        errorComponent: createFallbackComponent(viewId, "Failed to load dashboard"),
        delay: 200,
        timeout: 10000,
      })
    }

    return defineAsyncComponent({
      loader: () => this.loadViewComponent(viewId),
      loadingComponent: LoadingComponent,
      errorComponent: createFallbackComponent(viewId, "Failed to load component"),
      delay: 200,
      timeout: 10000,
    })
  }

  /**
   * Check if a view component is available
   */
  hasViewComponent(viewId: string): boolean {
    // Dashboard is always available (frontend component)
    if (viewId === "dashboard") {
      return true
    }
    // Check if we have a fallback path or it's in the available views
    // In dev mode, availableViews is populated from the dev manifest via getAvailableViews()
    return viewId in VIEW_FALLBACK_PATHS || this.availableViews.has(viewId)
  }
}

// Export singleton instance
export const viewPluginService = new ViewPluginService()
