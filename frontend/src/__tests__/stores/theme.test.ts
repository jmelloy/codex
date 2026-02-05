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

  it("initializes with default theme and returns correct theme object", () => {
    const store = useThemeStore()

    expect(store.currentTheme).toBe("cream")
    expect(store.theme).toEqual({
      name: "cream",
      label: "Cream",
      description: "Classic notebook with cream pages",
      className: "theme-cream",
    })
  })

  describe("initialize", () => {
    it("loads theme from localStorage or uses default for empty/invalid values", async () => {
      // Valid localStorage
      localStorage.setItem("codex-theme-preference", "cream")
      let store = useThemeStore()
      await store.initialize()
      expect(store.currentTheme).toBe("cream")

      // Empty localStorage
      setActivePinia(createPinia())
      localStorage.clear()
      store = useThemeStore()
      await store.initialize()
      expect(store.currentTheme).toBe("cream")

      // Invalid theme
      localStorage.setItem("codex-theme-preference", "invalid-theme")
      setActivePinia(createPinia())
      store = useThemeStore()
      await store.initialize()
      expect(store.currentTheme).toBe("cream")
    })
  })

  describe("setTheme", () => {
    it("updates theme, saves to localStorage when unauthenticated", async () => {
      vi.mocked(authService.isAuthenticated).mockReturnValue(false)

      const store = useThemeStore()
      await store.setTheme("manila")

      expect(store.currentTheme).toBe("manila")
      expect(localStorage.getItem("codex-theme-preference")).toBe("manila")
    })

    it("saves to user account when authenticated", async () => {
      vi.mocked(authService.isAuthenticated).mockReturnValue(true)
      vi.mocked(authService.updateTheme).mockResolvedValue({
        id: 1,
        username: "test",
        email: "test@example.com",
        is_active: true,
        theme_setting: "cream",
      })

      const store = useThemeStore()
      await store.setTheme("cream")

      expect(authService.updateTheme).toHaveBeenCalledWith("cream")
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
    it("loads user theme or falls back to localStorage/default", () => {
      // Valid user theme
      let store = useThemeStore()
      store.loadFromUser("cream")
      expect(store.currentTheme).toBe("cream")

      // Invalid user theme falls back to localStorage
      setActivePinia(createPinia())
      localStorage.setItem("codex-theme-preference", "manila")
      store = useThemeStore()
      store.loadFromUser("invalid-theme")
      expect(store.currentTheme).toBe("manila")

      // No user theme or localStorage falls back to default
      setActivePinia(createPinia())
      localStorage.clear()
      store = useThemeStore()
      store.loadFromUser(undefined)
      expect(store.currentTheme).toBe("cream")
    })
  })
})
