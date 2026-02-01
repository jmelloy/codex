/**
 * Plugin Registry Service
 *
 * Registers frontend-known plugins with the backend on app startup.
 * This implements the frontend-led plugin architecture where the frontend
 * declares which plugins it has, and the backend stores enabled/disabled
 * state and settings.
 */

import api from "./api"

/**
 * Plugin registration request
 */
export interface PluginRegistration {
  id: string
  name: string
  version: string
  type: "view" | "theme" | "integration"
  manifest: Record<string, unknown>
}

/**
 * Plugin registration response
 */
export interface PluginRegistrationResponse {
  id: string
  name: string
  version: string
  type: string
  registered: boolean
  message: string
}

/**
 * Batch registration response
 */
export interface BatchRegistrationResponse {
  registered: number
  updated: number
  failed: number
  results: PluginRegistrationResponse[]
}

/**
 * Known plugins in the frontend.
 * These are the plugins that ship with the frontend and should be registered
 * with the backend on startup.
 */
const KNOWN_PLUGINS: PluginRegistration[] = [
  // View plugins
  {
    id: "core",
    name: "Core",
    version: "1.0.0",
    type: "view",
    manifest: {
      id: "core",
      name: "Core",
      version: "1.0.0",
      type: "view",
      description: "Core view types and templates for journaling",
      views: [
        { id: "timeline", name: "Timeline", description: "Chronological file view", icon: "📅" },
        { id: "file-list", name: "File List", description: "Simple file listing", icon: "📄" },
      ],
      templates: [
        { id: "daily-journal", name: "Daily Journal", description: "Daily journaling template" },
        { id: "project-doc", name: "Project Document", description: "Project documentation template" },
        { id: "meeting-notes", name: "Meeting Notes", description: "Meeting notes template" },
        { id: "data-file", name: "Data File", description: "Data file template" },
        { id: "blank-note", name: "Blank Note", description: "Empty note template" },
      ],
    },
  },
  {
    id: "tasks",
    name: "Tasks",
    version: "1.0.0",
    type: "view",
    manifest: {
      id: "tasks",
      name: "Tasks",
      version: "1.0.0",
      type: "view",
      description: "Task management views",
      views: [
        { id: "kanban", name: "Kanban Board", description: "Kanban-style task board", icon: "📋" },
        { id: "task-list", name: "Task List", description: "List view for tasks", icon: "✅" },
      ],
      properties: [
        { name: "status", type: "string", enum: ["backlog", "todo", "in-progress", "review", "done"] },
        { name: "priority", type: "string", enum: ["low", "medium", "high", "critical"] },
        { name: "due_date", type: "date" },
        { name: "assignee", type: "string" },
        { name: "estimated_hours", type: "number" },
      ],
    },
  },
  {
    id: "gallery",
    name: "Gallery",
    version: "1.0.0",
    type: "view",
    manifest: {
      id: "gallery",
      name: "Gallery",
      version: "1.0.0",
      type: "view",
      description: "Image gallery view",
      views: [
        { id: "gallery", name: "Gallery", description: "Image gallery view", icon: "🖼️" },
      ],
    },
  },
  {
    id: "corkboard",
    name: "Corkboard",
    version: "1.0.0",
    type: "view",
    manifest: {
      id: "corkboard",
      name: "Corkboard",
      version: "1.0.0",
      type: "view",
      description: "Corkboard layout view",
      views: [
        { id: "corkboard", name: "Corkboard", description: "Corkboard layout", icon: "📌" },
      ],
    },
  },
  {
    id: "rollup",
    name: "Rollup",
    version: "1.0.0",
    type: "view",
    manifest: {
      id: "rollup",
      name: "Rollup",
      version: "1.0.0",
      type: "view",
      description: "Weekly summary rollup view",
      views: [
        { id: "rollup", name: "Rollup", description: "Weekly summary rollup", icon: "📊" },
      ],
    },
  },

  // Theme plugins
  {
    id: "cream",
    name: "Cream Theme",
    version: "1.0.0",
    type: "theme",
    manifest: {
      id: "cream",
      name: "Cream Theme",
      version: "1.0.0",
      type: "theme",
      theme: {
        display_name: "Cream",
        category: "light",
        className: "theme-cream",
      },
    },
  },
  {
    id: "manila",
    name: "Manila Theme",
    version: "1.0.0",
    type: "theme",
    manifest: {
      id: "manila",
      name: "Manila Theme",
      version: "1.0.0",
      type: "theme",
      theme: {
        display_name: "Manila",
        category: "light",
        className: "theme-manila",
      },
    },
  },
  {
    id: "white",
    name: "White Theme",
    version: "1.0.0",
    type: "theme",
    manifest: {
      id: "white",
      name: "White Theme",
      version: "1.0.0",
      type: "theme",
      theme: {
        display_name: "White",
        category: "light",
        className: "theme-white",
      },
    },
  },
  {
    id: "blueprint",
    name: "Blueprint Theme",
    version: "1.0.0",
    type: "theme",
    manifest: {
      id: "blueprint",
      name: "Blueprint Theme",
      version: "1.0.0",
      type: "theme",
      theme: {
        display_name: "Blueprint",
        category: "dark",
        className: "theme-blueprint",
      },
    },
  },

  // Integration plugins
  {
    id: "weather-api",
    name: "Weather API",
    version: "1.0.0",
    type: "integration",
    manifest: {
      id: "weather-api",
      name: "Weather API",
      version: "1.0.0",
      type: "integration",
      description: "OpenWeatherMap integration for weather data",
      integration: {
        api_type: "rest",
        base_url: "https://api.openweathermap.org/data/2.5",
        auth_method: "api_key",
      },
      properties: [
        { name: "api_key", type: "string", required: true, secure: true },
        { name: "default_location", type: "string", required: false },
        { name: "units", type: "string", enum: ["metric", "imperial"], default: "metric" },
      ],
      endpoints: [
        {
          id: "current_weather",
          name: "Current Weather",
          method: "GET",
          path: "/weather",
          parameters: [
            { name: "q", type: "string", required: true, description: "City name" },
            { name: "appid", type: "string", required: true, from_config: "api_key" },
            { name: "units", type: "string", from_config: "units" },
          ],
        },
        {
          id: "forecast",
          name: "Weather Forecast",
          method: "GET",
          path: "/forecast",
          parameters: [
            { name: "q", type: "string", required: true, description: "City name" },
            { name: "appid", type: "string", required: true, from_config: "api_key" },
            { name: "units", type: "string", from_config: "units" },
          ],
        },
      ],
      blocks: [
        { id: "weather", name: "Weather Widget", description: "Displays current weather", icon: "☀️" },
      ],
    },
  },
  {
    id: "opengraph",
    name: "OpenGraph",
    version: "1.0.0",
    type: "integration",
    manifest: {
      id: "opengraph",
      name: "OpenGraph",
      version: "1.0.0",
      type: "integration",
      description: "Link preview using OpenGraph metadata",
      integration: {},
      blocks: [
        { id: "link-preview", name: "Link Preview", description: "Rich link preview", icon: "🔗" },
      ],
    },
  },
  {
    id: "github",
    name: "GitHub",
    version: "1.0.0",
    type: "integration",
    manifest: {
      id: "github",
      name: "GitHub",
      version: "1.0.0",
      type: "integration",
      description: "GitHub integration for issues, PRs, and repos",
      integration: {
        api_type: "rest",
        base_url: "https://api.github.com",
        auth_method: "token",
      },
      properties: [
        { name: "access_token", type: "string", required: true, secure: true },
      ],
      endpoints: [
        {
          id: "get_repo",
          name: "Get Repository",
          method: "GET",
          path: "/repos/{owner}/{repo}",
          parameters: [
            { name: "owner", type: "string", required: true },
            { name: "repo", type: "string", required: true },
          ],
        },
        {
          id: "get_issue",
          name: "Get Issue",
          method: "GET",
          path: "/repos/{owner}/{repo}/issues/{issue_number}",
          parameters: [
            { name: "owner", type: "string", required: true },
            { name: "repo", type: "string", required: true },
            { name: "issue_number", type: "integer", required: true },
          ],
        },
      ],
      blocks: [
        { id: "github-issue", name: "GitHub Issue", description: "Display GitHub issue", icon: "🐛" },
        { id: "github-pr", name: "GitHub PR", description: "Display GitHub PR", icon: "🔀" },
        { id: "github-repo", name: "GitHub Repo", description: "Display GitHub repo", icon: "📦" },
      ],
    },
  },
]

class PluginRegistryService {
  private registered = false
  private registrationPromise: Promise<BatchRegistrationResponse> | null = null

  /**
   * Register all known plugins with the backend.
   * This should be called during app initialization.
   * Safe to call multiple times - will only register once.
   */
  async registerPlugins(): Promise<BatchRegistrationResponse> {
    if (this.registered) {
      return {
        registered: 0,
        updated: 0,
        failed: 0,
        results: [],
      }
    }

    if (this.registrationPromise) {
      return this.registrationPromise
    }

    this.registrationPromise = this._doRegister()

    try {
      const result = await this.registrationPromise
      this.registered = true
      return result
    } finally {
      this.registrationPromise = null
    }
  }

  private async _doRegister(): Promise<BatchRegistrationResponse> {
    try {
      const response = await api.post<BatchRegistrationResponse>(
        "/api/v1/plugins/register-batch",
        { plugins: KNOWN_PLUGINS }
      )
      console.log(
        `Plugins registered: ${response.data.registered} new, ${response.data.updated} updated, ${response.data.failed} failed`
      )
      return response.data
    } catch (error) {
      console.error("Failed to register plugins with backend:", error)
      // Return empty result on failure - plugins will work in frontend-only mode
      return {
        registered: 0,
        updated: 0,
        failed: KNOWN_PLUGINS.length,
        results: [],
      }
    }
  }

  /**
   * Get the list of known plugins.
   */
  getKnownPlugins(): PluginRegistration[] {
    return [...KNOWN_PLUGINS]
  }

  /**
   * Get plugins by type.
   */
  getPluginsByType(type: "view" | "theme" | "integration"): PluginRegistration[] {
    return KNOWN_PLUGINS.filter((p) => p.type === type)
  }

  /**
   * Check if a plugin is known by the frontend.
   */
  isPluginKnown(pluginId: string): boolean {
    return KNOWN_PLUGINS.some((p) => p.id === pluginId)
  }
}

// Export singleton instance
export const pluginRegistry = new PluginRegistryService()
