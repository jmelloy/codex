import apiClient from "./api"

export interface OAuthConnection {
  id: number
  provider: string
  provider_email: string | null
  scopes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OAuthAuthorizeResponse {
  authorization_url: string
}

export interface OAuthCallbackResponse {
  provider: string
  provider_email: string | null
  connected: boolean
}

export interface OAuthLoginCallbackResponse {
  access_token: string
  token_type: string
  provider_email: string | null
}

export const oauthService = {
  // --- Unauthenticated: Sign in / Sign up with Google ---

  async getGoogleLoginUrl(): Promise<OAuthAuthorizeResponse> {
    const response = await apiClient.get<OAuthAuthorizeResponse>("/api/v1/oauth/google/login")
    return response.data
  },

  async handleGoogleLoginCallback(code: string, state?: string): Promise<OAuthLoginCallbackResponse> {
    const response = await apiClient.post<OAuthLoginCallbackResponse>("/api/v1/oauth/google/login/callback", {
      code,
      state,
    })
    return response.data
  },

  // --- Authenticated: Connect Google account ---

  async getGoogleAuthUrl(): Promise<OAuthAuthorizeResponse> {
    const response = await apiClient.get<OAuthAuthorizeResponse>("/api/v1/oauth/google/authorize")
    return response.data
  },

  async handleGoogleCallback(code: string, state?: string): Promise<OAuthCallbackResponse> {
    const response = await apiClient.post<OAuthCallbackResponse>("/api/v1/oauth/google/callback", {
      code,
      state,
    })
    return response.data
  },

  async listConnections(): Promise<OAuthConnection[]> {
    const response = await apiClient.get<OAuthConnection[]>("/api/v1/oauth/connections")
    return response.data
  },

  async disconnectGoogle(): Promise<void> {
    await apiClient.delete("/api/v1/oauth/google/disconnect")
  },
}
