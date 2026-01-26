import { describe, it, expect, beforeEach, vi } from "vitest"
import { setActivePinia, createPinia } from "pinia"
import { useAuthStore } from "../../stores/auth"
import { authService } from "../../services/auth"

// Mock the auth service
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

describe("Auth Store", () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())

    // Clear localStorage
    localStorage.clear()

    // Reset mocks
    vi.clearAllMocks()
  })

  it("initializes with correct default values", () => {
    const store = useAuthStore()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it("successfully logs in and sets user", async () => {
    const store = useAuthStore()
    const mockTokenResponse = {
      access_token: "test-token",
      token_type: "bearer",
    }
    const mockUser = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      is_active: true,
    }

    vi.mocked(authService.login).mockResolvedValue(mockTokenResponse)
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

    await store.login("testuser", "password")

    expect(authService.login).toHaveBeenCalledWith({
      username: "testuser",
      password: "password",
    })
    expect(authService.saveToken).toHaveBeenCalledWith("test-token")
    expect(store.isAuthenticated).toBe(true)
    expect(store.user).toEqual(mockUser)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it("sets error on login failure", async () => {
    const store = useAuthStore()
    const mockError = {
      response: {
        data: {
          detail: "Invalid credentials",
        },
      },
    }

    vi.mocked(authService.login).mockRejectedValue(mockError)

    await expect(store.login("testuser", "wrong")).rejects.toThrow()

    expect(store.error).toBe("Invalid credentials")
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(store.loading).toBe(false)
  })

  it("handles generic login error", async () => {
    const store = useAuthStore()

    vi.mocked(authService.login).mockRejectedValue(new Error("Network error"))

    await expect(store.login("testuser", "password")).rejects.toThrow()

    expect(store.error).toBe("Login failed")
    expect(store.loading).toBe(false)
  })

  it("fetches current user successfully", async () => {
    const store = useAuthStore()
    const mockUser = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      is_active: true,
    }

    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

    await store.fetchCurrentUser()

    expect(store.user).toEqual(mockUser)
    expect(store.isAuthenticated).toBe(true)
  })

  it("logs out on failed user fetch", async () => {
    const store = useAuthStore()

    vi.mocked(authService.getCurrentUser).mockRejectedValue(new Error("Unauthorized"))

    await store.fetchCurrentUser()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(authService.logout).toHaveBeenCalled()
  })

  it("logs out and clears user state", () => {
    const store = useAuthStore()

    // Set initial state
    store.user = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      is_active: true,
    }
    store.isAuthenticated = true

    store.logout()

    expect(authService.logout).toHaveBeenCalled()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it("initializes user if authenticated", async () => {
    const store = useAuthStore()
    const mockUser = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      is_active: true,
    }

    vi.mocked(authService.isAuthenticated).mockReturnValue(true)
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

    await store.initialize()

    expect(authService.isAuthenticated).toHaveBeenCalled()
    expect(authService.getCurrentUser).toHaveBeenCalled()
    expect(store.user).toEqual(mockUser)
    expect(store.isAuthenticated).toBe(true)
  })

  it("does not fetch user if not authenticated", async () => {
    const store = useAuthStore()

    vi.mocked(authService.isAuthenticated).mockReturnValue(false)

    await store.initialize()

    expect(authService.isAuthenticated).toHaveBeenCalled()
    expect(authService.getCurrentUser).not.toHaveBeenCalled()
    expect(store.user).toBeNull()
  })

  it("sets loading state during login", async () => {
    const store = useAuthStore()
    const mockTokenResponse = {
      access_token: "test-token",
      token_type: "bearer",
    }
    const mockUser = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      is_active: true,
    }

    vi.mocked(authService.login).mockImplementation(async () => {
      expect(store.loading).toBe(true)
      return mockTokenResponse
    })
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

    await store.login("testuser", "password")

    expect(store.loading).toBe(false)
  })

  it("clears error on successful login", async () => {
    const store = useAuthStore()
    const mockTokenResponse = {
      access_token: "test-token",
      token_type: "bearer",
    }
    const mockUser = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      is_active: true,
    }

    // Set initial error
    store.error = "Previous error"

    vi.mocked(authService.login).mockResolvedValue(mockTokenResponse)
    vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

    await store.login("testuser", "password")

    expect(store.error).toBeNull()
  })
})
