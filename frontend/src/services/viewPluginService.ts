/**
 * View Plugin Service
 *
 * Manages dynamic loading of view components from the plugin system.
 * View components are built by the plugin build script (plugins/build.ts)
 * and output to plugins/{plugin}/dist/{view}.js
 */

import { defineAsyncComponent, h, type Component } from "vue"
import { getAvailableViews, getAvailableBlockTypes } from "./pluginLoader"

export interface ViewPlugin {
  id: string
  name: string
  description: string
  icon?: string
  plugin_id: string
  plugin_name: string
  config_schema?: Record<string, any>
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
    // Ensure service is initialized before loading
    if (!this.initialized) {
      await this.initialize()
    }

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

    // Production path: look up the compiled component file from the plugin manifest
    // The plugin loader's block types map includes view components (keyed by view ID)
    const blockTypes = await getAvailableBlockTypes()
    const blockEntry = blockTypes.find((b) => b.blockType === viewId)

    if (blockEntry) {
      // Found in plugin manifest's component map — use the file path directly
      try {
        const { loadPluginComponent } = await import("./pluginLoader")
        const component = loadPluginComponent(viewId)
        // loadPluginComponent returns an async component wrapper; resolve it
        return component
      } catch (err) {
        console.warn(`Failed to load view via plugin component map for ${viewId}:`, err)
      }
    }

    // Fallback: construct URL from view metadata (plugin_id + naming convention)
    const view = this.availableViews.get(viewId)
    const pluginId = view?.plugin_id || viewId
    const distName = `${viewId}-view`
    try {
      const moduleUrl = `${PLUGINS_BASE}/${pluginId}/dist/${distName}.js`
      const module = await import(/* @vite-ignore */ moduleUrl)
      return module.default || module
    } catch (err) {
      console.warn(`Failed to load compiled view component for ${viewId}:`, err)
    }

    // Return fallback component
    return createFallbackComponent(viewId)
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
    // Check if the view is registered from the plugin manifest
    return this.availableViews.has(viewId)
  }
}

// Export singleton instance
export const viewPluginService = new ViewPluginService()
