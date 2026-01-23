import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { workspaceService } from "../services/codex"

export type ThemeName = "cream" | "manila" | "white" | "blueprint"

export interface Theme {
  name: ThemeName
  label: string
  description: string
  className: string
}

const THEMES: Theme[] = [
  {
    name: "cream",
    label: "Cream",
    description: "Classic notebook with cream pages",
    className: "theme-cream",
  },
  {
    name: "manila",
    label: "Manila",
    description: "Vintage manila folder aesthetic",
    className: "theme-manila",
  },
  {
    name: "white",
    label: "White",
    description: "Clean white pages",
    className: "theme-white",
  },
  {
    name: "blueprint",
    label: "Blueprint",
    description: "Dark mode with blueprint styling",
    className: "theme-blueprint",
  },
]

const STORAGE_KEY = "codex-theme-preference"
const DEFAULT_THEME: ThemeName = "cream"

export const useThemeStore = defineStore("theme", () => {
  const currentTheme = ref<ThemeName>(DEFAULT_THEME)
  const currentWorkspaceId = ref<number | null>(null)

  const theme = computed((): Theme => {
    const found = THEMES.find((t) => t.name === currentTheme.value)
    return found ?? THEMES[0]!
  })

  const availableThemes = computed(() => THEMES)

  async function setTheme(themeName: ThemeName) {
    currentTheme.value = themeName

    // Save to workspace if available
    if (currentWorkspaceId.value) {
      try {
        const updatedWorkspace = await workspaceService.updateTheme(currentWorkspaceId.value, themeName)

        // Update the workspace store's current workspace object with the new theme
        // Import inside function to avoid circular dependency issues
        const { useWorkspaceStore } = await import("./workspace")
        const workspaceStore = useWorkspaceStore()

        // Update currentWorkspace if it's the same workspace
        if (workspaceStore.currentWorkspace?.id === currentWorkspaceId.value) {
          workspaceStore.currentWorkspace.theme_setting = updatedWorkspace.theme_setting
        }

        // Also update in the workspaces list
        const workspaceIndex = workspaceStore.workspaces.findIndex(w => w.id === currentWorkspaceId.value)
        if (workspaceIndex !== -1 && workspaceStore.workspaces[workspaceIndex]) {
          workspaceStore.workspaces[workspaceIndex]!.theme_setting = updatedWorkspace.theme_setting
        }
      } catch (error) {
        console.error("Failed to save theme to workspace:", error)
        // Fallback to localStorage on error
        saveToLocalStorage(themeName)
      }
    } else {
      // No workspace, use localStorage
      saveToLocalStorage(themeName)
    }
  }

  function saveToLocalStorage(themeName: ThemeName) {
    try {
      localStorage.setItem(STORAGE_KEY, themeName)
    } catch (error) {
      console.error("Failed to save theme preference:", error)
    }
  }

  function loadFromLocalStorage(): ThemeName {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved && THEMES.some((t) => t.name === saved)) {
        return saved as ThemeName
      }
    } catch (error) {
      console.error("Failed to load theme preference:", error)
    }
    return DEFAULT_THEME
  }

  function loadFromWorkspace(workspaceId: number, themeSetting?: string) {
    currentWorkspaceId.value = workspaceId

    if (themeSetting && THEMES.some((t) => t.name === themeSetting)) {
      currentTheme.value = themeSetting as ThemeName
    } else {
      // Fallback to localStorage if workspace doesn't have a theme
      currentTheme.value = loadFromLocalStorage()
    }
  }

  function initialize() {
    currentTheme.value = loadFromLocalStorage()
  }

  return {
    currentTheme,
    theme,
    availableThemes,
    setTheme,
    initialize,
    loadFromWorkspace,
  }
})
