import { ref, computed } from "vue";
import { defineStore } from "pinia";

export interface User {
  id: number;
  username: string;
  email: string;
  workspace_path: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

const API_BASE = "/api";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem("auth_token"));
  const refreshToken = ref<string | null>(localStorage.getItem("refresh_token"));
  const user = ref<User | null>(
    localStorage.getItem("user")
      ? JSON.parse(localStorage.getItem("user")!)
      : null,
  );
  const loading = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  async function register(
    username: string,
    email: string,
    password: string,
  ): Promise<boolean> {
    loading.value = true;
    error.value = null;

    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Registration failed");
      }

      const data: LoginResponse = await response.json();
      setAuth(data);
      return true;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Registration failed";
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true;
    error.value = null;

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Login failed");
      }

      const data: LoginResponse = await response.json();
      setAuth(data);
      return true;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Login failed";
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function fetchCurrentUser(): Promise<boolean> {
    if (!token.value) return false;

    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token.value}`,
        },
      });

      if (!response.ok) {
        logout();
        return false;
      }

      const data: User = await response.json();
      user.value = data;
      localStorage.setItem("user", JSON.stringify(data));
      return true;
    } catch (e) {
      logout();
      return false;
    }
  }

  function setAuth(data: LoginResponse) {
    token.value = data.access_token;
    refreshToken.value = data.refresh_token;
    user.value = data.user;
    localStorage.setItem("auth_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    error.value = null;
  }

  function logout() {
    token.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    error.value = null;
  }

  function clearError() {
    error.value = null;
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false;

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      });

      if (!response.ok) {
        logout();
        return false;
      }

      const data = await response.json();
      token.value = data.access_token;
      localStorage.setItem("auth_token", data.access_token);
      return true;
    } catch (e) {
      logout();
      return false;
    }
  }

  return {
    token,
    refreshToken,
    user,
    loading,
    error,
    isAuthenticated,
    register,
    login,
    logout,
    fetchCurrentUser,
    refreshAccessToken,
    clearError,
  };
});
