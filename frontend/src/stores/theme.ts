import { defineStore } from "pinia"
import { ref, computed } from "vue"

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

  const theme = computed((): Theme => {
    const found = THEMES.find((t) => t.name === currentTheme.value)
    return found ?? THEMES[0]!
  })

  const availableThemes = computed(() => THEMES)

  function setTheme(themeName: ThemeName) {
    currentTheme.value = themeName
    saveToLocalStorage(themeName)
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

  function initialize() {
    currentTheme.value = loadFromLocalStorage()
  }

  return {
    currentTheme,
    theme,
    availableThemes,
    setTheme,
    initialize,
  }
})
