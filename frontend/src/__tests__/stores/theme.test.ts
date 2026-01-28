import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useThemeStore } from "../../stores/theme"
import { authService } from "../../services/auth"

// Mock the auth service
vi.mock("../../services/auth", () => ({
  authService: {
    isAuthenticated: vi.fn(),
    updateTheme: vi.fn(),
  },
}))

// Mock the auth store for dynamic import
vi.mock("../../stores/auth", () => ({
  useAuthStore: () => ({
    user: { id: 1, username: "test", theme_setting: "cream" },
  }),
}))

describe("Theme Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it("initializes with default theme", () => {
    const store = useThemeStore()

    expect(store.currentTheme).toBe("cream")
    expect(store.theme.name).toBe("cream")
  })

  it("provides all available themes", () => {
    const store = useThemeStore()

    expect(store.availableThemes).toHaveLength(4)
    expect(store.availableThemes.map((t) => t.name)).toEqual([
      "cream",
      "manila",
      "white",
      "blueprint",
    ])
  })

  it("returns correct theme object", () => {
    const store = useThemeStore()

    expect(store.theme).toEqual({
      name: "cream",
      label: "Cream",
      description: "Classic notebook with cream pages",
      className: "theme-cream",
    })
  })

  describe("initialize", () => {
    it("loads theme from localStorage on initialize", () => {
      localStorage.setItem("codex-theme-preference", "blueprint")

      const store = useThemeStore()
      store.initialize()

      expect(store.currentTheme).toBe("blueprint")
    })

    it("uses default theme when localStorage is empty", () => {
      const store = useThemeStore()
      store.initialize()

      expect(store.currentTheme).toBe("cream")
    })

    it("ignores invalid theme in localStorage", () => {
      localStorage.setItem("codex-theme-preference", "invalid-theme")

      const store = useThemeStore()
      store.initialize()

      expect(store.currentTheme).toBe("cream")
    })
  })

  describe("setTheme", () => {
    it("updates current theme", async () => {
      vi.mocked(authService.isAuthenticated).mockReturnValue(false)

      const store = useThemeStore()
      await store.setTheme("manila")

      expect(store.currentTheme).toBe("manila")
    })

    it("saves to localStorage when not authenticated", async () => {
      vi.mocked(authService.isAuthenticated).mockReturnValue(false)

      const store = useThemeStore()
      await store.setTheme("white")

      expect(localStorage.getItem("codex-theme-preference")).toBe("white")
    })

    it("saves to user account when authenticated", async () => {
      vi.mocked(authService.isAuthenticated).mockReturnValue(true)
      vi.mocked(authService.updateTheme).mockResolvedValue({
        id: 1,
        username: "test",
        email: "test@example.com",
        is_active: true,
        theme_setting: "blueprint",
      })

      const store = useThemeStore()
      await store.setTheme("blueprint")

      expect(authService.updateTheme).toHaveBeenCalledWith("blueprint")
    })

    it("falls back to localStorage when API fails", async () => {
      vi.mocked(authService.isAuthenticated).mockReturnValue(true)
      vi.mocked(authService.updateTheme).mockRejectedValue(new Error("API error"))

      const store = useThemeStore()
      await store.setTheme("manila")

      expect(store.currentTheme).toBe("manila")
      expect(localStorage.getItem("codex-theme-preference")).toBe("manila")
    })
  })

  describe("loadFromUser", () => {
    it("loads theme from user setting", () => {
      const store = useThemeStore()
      store.loadFromUser("blueprint")

      expect(store.currentTheme).toBe("blueprint")
    })

    it("falls back to localStorage when user has no theme", () => {
      localStorage.setItem("codex-theme-preference", "manila")

      const store = useThemeStore()
      store.loadFromUser(undefined)

      expect(store.currentTheme).toBe("manila")
    })

    it("falls back to localStorage for invalid user theme", () => {
      localStorage.setItem("codex-theme-preference", "white")

      const store = useThemeStore()
      store.loadFromUser("invalid-theme")

      expect(store.currentTheme).toBe("white")
    })

    it("uses default when both user and localStorage are empty", () => {
      const store = useThemeStore()
      store.loadFromUser(undefined)

      expect(store.currentTheme).toBe("cream")
    })
  })

  describe("theme computed", () => {
    it("returns full theme object for current theme", () => {
      const store = useThemeStore()

      store.currentTheme = "blueprint"

      expect(store.theme).toEqual({
        name: "blueprint",
        label: "Blueprint",
        description: "Dark mode with blueprint styling",
        className: "theme-blueprint",
      })
    })

    it("falls back to first theme for invalid current theme", () => {
      const store = useThemeStore()

      // Force an invalid theme (shouldn't happen in practice)
      store.currentTheme = "nonexistent" as any

      expect(store.theme.name).toBe("cream")
    })
  })
})
