import apiClient from "./api"

export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
  theme_setting?: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// Helper to set the access token cookie (for browser-initiated requests like <img src>)
function setTokenCookie(token: string) {
  // Set cookie with SameSite=Strict for security, path=/ for all routes
  document.cookie = `access_token=${token}; path=/; SameSite=Strict`
}

// Helper to remove the access token cookie
function removeTokenCookie() {
  document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
}

// Helper to save token to both localStorage and cookie
function saveToken(token: string) {
  localStorage.setItem("access_token", token)
  setTokenCookie(token)
}

// Helper to clear token from both localStorage and cookie
function clearToken() {
  localStorage.removeItem("access_token")
  removeTokenCookie()
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const params = new URLSearchParams()
    params.append("username", credentials.username)
    params.append("password", credentials.password)

    const response = await apiClient.post<TokenResponse>("/api/v1/users/token", params, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    })
    return response.data
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>("/api/v1/users/me")
    return response.data
  },

  async register(data: RegisterData): Promise<User> {
    const response = await apiClient.post<User>("/api/v1/users/register", data)
    return response.data
  },

  logout() {
    clearToken()
  },

  isAuthenticated(): boolean {
    const token = localStorage.getItem("access_token")
    if (token) {
      // Ensure cookie is in sync (for existing sessions before cookie support)
      setTokenCookie(token)
      return true
    }
    return false
  },

  // Save token (use this instead of directly setting localStorage)
  saveToken,

  async updateTheme(theme: string): Promise<User> {
    const response = await apiClient.patch<User>("/api/v1/users/me/theme", {
      theme,
    })
    return response.data
  },
}
