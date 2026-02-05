import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { authService } from "../services/auth"
import {
  getAvailableThemes,
  getThemeStylesheetUrl,
  type PluginTheme,
} from "../services/pluginLoader"

export type ThemeName = string

export interface Theme {
  name: ThemeName
  label: string
  description: string
  className: string
  category?: string
  version?: string
  stylesheet?: string
}

// Default fallback themes if plugins fail to load
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
    return found ?? themes.value[0] ?? DEFAULT_THEMES[0]!
  })

  const availableThemes = computed(() => themes.value)

  async function loadThemes() {
    // Only load once unless there was an error
    if (themesLoaded.value && !themesLoadError.value) return

    try {
      const pluginThemes = await getAvailableThemes()

      if (pluginThemes.length > 0) {
        // Convert plugin themes to store format
        themes.value = pluginThemes.map((t: PluginTheme) => ({
          name: t.name,
          label: t.label,
          description: t.description,
          className: t.className,
          category: t.category,
          version: t.version,
          stylesheet: t.stylesheet,
        }))
      } else {
        // Keep using DEFAULT_THEMES as fallback
        themes.value = DEFAULT_THEMES
      }

      themesLoaded.value = true
      themesLoadError.value = false
    } catch (error) {
      console.error("Failed to load themes from plugins:", error)
      // Keep using DEFAULT_THEMES as fallback
      themes.value = DEFAULT_THEMES
      themesLoadError.value = true
    }
  }

  async function setTheme(themeName: ThemeName) {
    currentTheme.value = themeName

    // Load the theme stylesheet dynamically
    await loadThemeStylesheet(themeName)

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

  async function loadThemeStylesheet(themeName: ThemeName) {
    // Remove any existing theme stylesheets
    const existingLinks = document.querySelectorAll("link[data-theme-stylesheet]")
    existingLinks.forEach((link) => link.remove())

    // Find the theme to get its stylesheet path
    const themeData = themes.value.find((t) => t.name === themeName)
    const stylesheetUrl = getThemeStylesheetUrl(themeName, themeData?.stylesheet)

    // Create and append new stylesheet link
    const link = document.createElement("link")
    link.rel = "stylesheet"
    link.href = stylesheetUrl
    link.setAttribute("data-theme-stylesheet", themeName)

    // Add error handling
    link.onerror = () => {
      console.error(`Failed to load stylesheet for theme: ${themeName}`)
    }

    document.head.appendChild(link)
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

  async function loadFromUser(themeSetting?: string) {
    if (themeSetting && themes.value.some((t) => t.name === themeSetting)) {
      currentTheme.value = themeSetting as ThemeName
    } else {
      // Fallback to localStorage if user doesn't have a theme
      currentTheme.value = loadFromLocalStorage()
    }
    // Load the theme stylesheet
    await loadThemeStylesheet(currentTheme.value)
  }

  async function initialize() {
    // Load themes from plugins first
    await loadThemes()

    // Then set the current theme from localStorage
    currentTheme.value = loadFromLocalStorage()

    // Load the theme stylesheet
    await loadThemeStylesheet(currentTheme.value)
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
