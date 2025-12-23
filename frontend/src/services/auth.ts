import apiClient from "./api";

export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const formData = new FormData();
    formData.append("username", credentials.username);
    formData.append("password", credentials.password);

    const response = await apiClient.post<TokenResponse>("/token", formData);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>("/users/me");
    return response.data;
  },

  logout() {
    localStorage.removeItem("access_token");
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem("access_token");
  },
};
