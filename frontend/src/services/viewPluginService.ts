/**
 * View Plugin Service
 * 
 * Manages dynamic loading of view components from the plugin system.
 */

import api from "./api"

export interface ViewPlugin {
  id: string
  name: string
  description: string
  icon: string
  plugin_id: string
  plugin_name: string
  config_schema: Record<string, any>
}

class ViewPluginService {
  private availableViews: Map<string, ViewPlugin> = new Map()
  private viewComponents: Map<string, any> = new Map()
  private initialized = false
  private initPromise: Promise<void> | null = null

  /**
   * Initialize the view plugin service by fetching available views from the API
   * This method is safe to call multiple times - it will only initialize once
   */
  async initialize(): Promise<void> {
    // Return existing promise if initialization is in progress
    if (this.initPromise) {
      return this.initPromise
    }

    // Return immediately if already initialized
    if (this.initialized) {
      return
    }

    // Create and store the initialization promise
    this.initPromise = this._doInitialize()
    
    try {
      await this.initPromise
    } finally {
      this.initPromise = null
    }
  }

  private async _doInitialize(): Promise<void> {
    try {
      const response = await api.get<ViewPlugin[]>("/api/v1/views")
      const views = response.data

      // Store views in a map by their ID
      for (const view of views) {
        this.availableViews.set(view.id, view)
      }

      // Register built-in view components
      this.registerBuiltInComponents()

      this.initialized = true
    } catch (error) {
      console.error("Failed to load available views:", error)
      // Still register built-in components as fallback
      this.registerBuiltInComponents()
      this.initialized = true
    }
  }

  /**
   * Register the built-in view components
   * These are statically imported from the frontend codebase
   */
  private registerBuiltInComponents(): void {
    // Lazy-load view components
    this.viewComponents.set("kanban", () => import("@/components/views/KanbanView.vue"))
    this.viewComponents.set("task-list", () => import("@/components/views/TaskListView.vue"))
    this.viewComponents.set("rollup", () => import("@/components/views/RollupView.vue"))
    this.viewComponents.set("gallery", () => import("@/components/views/GalleryView.vue"))
    this.viewComponents.set("corkboard", () => import("@/components/views/CorkboardView.vue"))
    this.viewComponents.set("dashboard", () => import("@/components/views/DashboardView.vue"))
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
   */
  async loadViewComponent(viewId: string): Promise<any> {
    const loader = this.viewComponents.get(viewId)
    if (!loader) {
      throw new Error(`View component not found: ${viewId}`)
    }

    const module = await loader()
    return module.default
  }

  /**
   * Check if a view component is registered
   */
  hasViewComponent(viewId: string): boolean {
    return this.viewComponents.has(viewId)
  }
}

// Export singleton instance
export const viewPluginService = new ViewPluginService()
