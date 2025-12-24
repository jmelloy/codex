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

export interface RegisterData {
  username: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const formData = new URLSearchParams();
    formData.append("username", credentials.username);
    formData.append("password", credentials.password);

    const response = await apiClient.post<TokenResponse>("/token", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>("/users/me");
    return response.data;
  },

  async register(data: RegisterData): Promise<User> {
    const response = await apiClient.post<User>("/register", data);
    return response.data;
  },

  logout() {
    localStorage.removeItem("access_token");
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem("access_token");
  },
};
