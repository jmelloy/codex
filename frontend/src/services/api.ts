import axios from "axios"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ""

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

// Add token to requests; let axios set Content-Type for FormData
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"]
  }
  return config
})

// Exchange the httponly refresh_token cookie for a new access token.
// Exported so services/auth.ts can expose it as part of the public auth API.
export async function refreshAccessToken(): Promise<string> {
  const response = await apiClient.post<{ access_token: string }>("/api/v1/auth/refresh", undefined, {
    withCredentials: true,
  })
  const token = response.data.access_token
  localStorage.setItem("access_token", token)
  document.cookie = `access_token=${token}; path=/; SameSite=Strict`
  return token
}

// Auth endpoints that must never trigger a refresh-and-retry (avoids infinite loops).
const NO_REFRESH_PATHS = ["/api/v1/users/token", "/api/v1/auth/refresh"]

function clearSessionAndRedirect() {
  localStorage.removeItem("access_token")
  // Also clear the cookie
  document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
  // Only redirect if not already on login page to avoid doom loop
  if (!window.location.pathname.startsWith("/login")) {
    window.location.href = "/login"
  }
}

// Ensures concurrent 401s only trigger a single refresh request.
let pendingRefresh: Promise<string> | null = null

// Handle 401 errors: try a token refresh once before giving up on the session.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const isAuthEndpoint = NO_REFRESH_PATHS.some((path) => originalRequest?.url?.includes(path))

    if (error.response?.status === 401 && originalRequest && !originalRequest._retried && !isAuthEndpoint) {
      originalRequest._retried = true
      try {
        pendingRefresh ??= refreshAccessToken().finally(() => {
          pendingRefresh = null
        })
        const newToken = await pendingRefresh
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch {
        clearSessionAndRedirect()
        return Promise.reject(error)
      }
    }

    if (error.response?.status === 401) {
      clearSessionAndRedirect()
    }
    return Promise.reject(error)
  },
)

export default apiClient
