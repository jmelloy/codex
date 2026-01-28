import { describe, it, expect, beforeEach, vi, type Mock } from "vitest"
import apiClient from "../../services/api"
import { authService } from "../../services/auth"

// Mock the api client
vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}))

describe("Auth Service", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    // Clear any existing cookies
    document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
  })

  describe("login", () => {
    it("sends form-urlencoded credentials", async () => {
      const mockResponse = { access_token: "test-token", token_type: "bearer" }
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockResponse })

      const result = await authService.login({ username: "testuser", password: "testpass" })

      expect(apiClient.post).toHaveBeenCalledWith(
        "/api/token",
        expect.any(URLSearchParams),
        expect.objectContaining({
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        })
      )
      expect(result).toEqual(mockResponse)

      // Verify URLSearchParams content
      const params = (apiClient.post as Mock).mock.calls[0][1] as URLSearchParams
      expect(params.get("username")).toBe("testuser")
      expect(params.get("password")).toBe("testpass")
    })
  })

  describe("getCurrentUser", () => {
    it("fetches current user from API", async () => {
      const mockUser = { id: 1, username: "testuser", email: "test@example.com", is_active: true }
      ;(apiClient.get as Mock).mockResolvedValue({ data: mockUser })

      const result = await authService.getCurrentUser()

      expect(apiClient.get).toHaveBeenCalledWith("/api/users/me")
      expect(result).toEqual(mockUser)
    })
  })

  describe("register", () => {
    it("registers a new user", async () => {
      const mockUser = { id: 1, username: "newuser", email: "new@example.com", is_active: true }
      ;(apiClient.post as Mock).mockResolvedValue({ data: mockUser })

      const result = await authService.register({
        username: "newuser",
        email: "new@example.com",
        password: "password123",
      })

      expect(apiClient.post).toHaveBeenCalledWith("/api/register", {
        username: "newuser",
        email: "new@example.com",
        password: "password123",
      })
      expect(result).toEqual(mockUser)
    })
  })

  describe("saveToken", () => {
    it("saves token to localStorage", () => {
      authService.saveToken("my-token")

      expect(localStorage.getItem("access_token")).toBe("my-token")
    })

    it("saves token to cookie", () => {
      authService.saveToken("my-token")

      expect(document.cookie).toContain("access_token=my-token")
    })
  })

  describe("logout", () => {
    it("removes token from localStorage", () => {
      localStorage.setItem("access_token", "my-token")

      authService.logout()

      expect(localStorage.getItem("access_token")).toBeNull()
    })

    it("removes token cookie", () => {
      document.cookie = "access_token=my-token; path=/"

      authService.logout()

      // Cookie should be expired
      expect(document.cookie).not.toContain("access_token=my-token")
    })
  })

  describe("isAuthenticated", () => {
    it("returns true when token exists in localStorage", () => {
      localStorage.setItem("access_token", "my-token")

      const result = authService.isAuthenticated()

      expect(result).toBe(true)
    })

    it("returns false when no token exists", () => {
      const result = authService.isAuthenticated()

      expect(result).toBe(false)
    })

    it("syncs localStorage token to cookie", () => {
      localStorage.setItem("access_token", "my-token")
      // Ensure cookie is not set yet
      document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"

      authService.isAuthenticated()

      expect(document.cookie).toContain("access_token=my-token")
    })
  })

  describe("updateTheme", () => {
    it("updates user theme setting", async () => {
      const mockUser = { id: 1, username: "testuser", theme_setting: "blueprint" }
      ;(apiClient.patch as Mock).mockResolvedValue({ data: mockUser })

      const result = await authService.updateTheme("blueprint")

      expect(apiClient.patch).toHaveBeenCalledWith("/api/users/me/theme", { theme: "blueprint" })
      expect(result).toEqual(mockUser)
    })
  })
})
