import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { authService } from "../services/auth"
import { themeService, type Theme as ApiTheme } from "../services/codex"

export type ThemeName = string

export interface Theme {
  name: ThemeName
  label: string
  description: string
  className: string
  category?: string
  version?: string
  author?: string
}

// Default fallback themes if API fails
const DEFAULT_THEMES: Theme[] = [
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
  const themes = ref<Theme[]>(DEFAULT_THEMES)
  const themesLoaded = ref(false)
  const themesLoadError = ref(false)

  const theme = computed((): Theme => {
    const found = themes.value.find((t) => t.name === currentTheme.value)
    // Ensure we always return a valid theme, falling back to DEFAULT_THEMES if needed
    return found ?? themes.value[0] ?? DEFAULT_THEMES[0]
  })

  const availableThemes = computed(() => themes.value)

  async function loadThemes() {
    // Only load once unless there was an error
    if (themesLoaded.value && !themesLoadError.value) return

    try {
      const apiThemes = await themeService.list()
      
      // Convert API themes to store format
      themes.value = apiThemes.map((t: ApiTheme) => ({
        name: t.name,
        label: t.label,
        description: t.description,
        className: t.className,
        category: t.category,
        version: t.version,
        author: t.author,
      }))
      
      themesLoaded.value = true
      themesLoadError.value = false
    } catch (error) {
      console.error("Failed to load themes from API:", error)
      // Keep using DEFAULT_THEMES as fallback
      themes.value = DEFAULT_THEMES
      themesLoadError.value = true
    }
  }

  async function setTheme(themeName: ThemeName) {
    currentTheme.value = themeName

    // Save to user account if authenticated
    if (authService.isAuthenticated()) {
      try {
        const updatedUser = await authService.updateTheme(themeName)

        // Update the auth store's user object with the new theme
        // Import inside function to avoid circular dependency issues
        const { useAuthStore } = await import("./auth")
        const authStore = useAuthStore()

        if (authStore.user) {
          authStore.user.theme_setting = updatedUser.theme_setting
        }
      } catch (error) {
        console.error("Failed to save theme to user:", error)
        // Fallback to localStorage on error
        saveToLocalStorage(themeName)
      }
    } else {
      // No user logged in, use localStorage
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
      if (saved && themes.value.some((t) => t.name === saved)) {
        return saved as ThemeName
      }
    } catch (error) {
      console.error("Failed to load theme preference:", error)
    }
    return DEFAULT_THEME
  }

  function loadFromUser(themeSetting?: string) {
    if (themeSetting && themes.value.some((t) => t.name === themeSetting)) {
      currentTheme.value = themeSetting as ThemeName
    } else {
      // Fallback to localStorage if user doesn't have a theme
      currentTheme.value = loadFromLocalStorage()
    }
  }

  async function initialize() {
    // Load themes from API first
    await loadThemes()
    
    // Then set the current theme from localStorage
    currentTheme.value = loadFromLocalStorage()
  }

  return {
    currentTheme,
    theme,
    availableThemes,
    setTheme,
    initialize,
    loadFromUser,
    loadThemes,
  }
})
