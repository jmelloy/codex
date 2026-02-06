import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useAuthStore } from "../../stores/auth"
import { authService } from "../../services/auth"

vi.mock("../../services/auth", () => ({
  authService: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    isAuthenticated: vi.fn(),
    saveToken: vi.fn(),
  },
}))

vi.mock("../../stores/integration", () => ({
  useIntegrationStore: () => ({
    loadIntegrations: vi.fn().mockResolvedValue(undefined),
    reset: vi.fn(),
  }),
}))

vi.mock("../../services/pluginRegistry", () => ({
  pluginRegistry: {
    registerPlugins: vi.fn().mockResolvedValue({ registered: 0, updated: 0, failed: 0, results: [] }),
  },
}))

vi.mock("../../services/viewPluginService", () => ({
  viewPluginService: { initialize: vi.fn().mockResolvedValue(undefined) },
}))

const mockTokenResponse = { access_token: "test-token", token_type: "bearer" }
const mockUser = { id: 1, username: "testuser", email: "test@example.com", is_active: true }

describe("Auth Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it("initializes with correct default values", () => {
    const store = useAuthStore()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it("successfully logs in, sets user, clears previous error", async () => {
    const store = useAuthStore()
    store.error = "Previous error"

    vi.mocked(authService.login).mockResolvedValue(mockTokenResponse)
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

    await store.login("testuser", "password")

    expect(authService.login).toHaveBeenCalledWith({ username: "testuser", password: "password" })
    expect(authService.saveToken).toHaveBeenCalledWith("test-token")
    expect(store.isAuthenticated).toBe(true)
    expect(store.user).toEqual(mockUser)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it("sets error on login failure (detailed and generic)", async () => {
    const store = useAuthStore()

    // Detailed error from API
    vi.mocked(authService.login).mockRejectedValue({
      response: { data: { detail: "Invalid credentials" } },
    })
    await expect(store.login("testuser", "wrong")).rejects.toThrow()
    expect(store.error).toBe("Invalid credentials")
    expect(store.isAuthenticated).toBe(false)
    expect(store.loading).toBe(false)

    // Generic error
    vi.clearAllMocks()
    const store2 = useAuthStore()
    vi.mocked(authService.login).mockRejectedValue(new Error("Network error"))
    await expect(store2.login("testuser", "password")).rejects.toThrow()
    expect(store2.error).toBe("Login failed")
  })

  it("fetches current user successfully or logs out on failure", async () => {
    const store = useAuthStore()

    // Success
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)
    await store.fetchCurrentUser()
    expect(store.user).toEqual(mockUser)
    expect(store.isAuthenticated).toBe(true)

    // Failure
    vi.mocked(authService.getCurrentUser).mockRejectedValue(new Error("Unauthorized"))
    await store.fetchCurrentUser()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(authService.logout).toHaveBeenCalled()
  })

  it("logs out and clears user state", () => {
    const store = useAuthStore()
    store.user = mockUser
    store.isAuthenticated = true

    store.logout()

    expect(authService.logout).toHaveBeenCalled()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it("initializes user if authenticated, skips if not", async () => {
    const store = useAuthStore()

    // Authenticated
    vi.mocked(authService.isAuthenticated).mockReturnValue(true)
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)
    await store.initialize()
    expect(store.user).toEqual(mockUser)
    expect(store.isAuthenticated).toBe(true)

    // Not authenticated
    setActivePinia(createPinia())
    const store2 = useAuthStore()
    vi.mocked(authService.isAuthenticated).mockReturnValue(false)
    await store2.initialize()
    expect(authService.getCurrentUser).toHaveBeenCalledTimes(1) // only from first test
    expect(store2.user).toBeNull()
  })

  it("sets loading state during login", async () => {
    const store = useAuthStore()
    vi.mocked(authService.login).mockImplementation(async () => {
      expect(store.loading).toBe(true)
      return mockTokenResponse
    })
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

    await store.login("testuser", "password")
    expect(store.loading).toBe(false)
  })
})
