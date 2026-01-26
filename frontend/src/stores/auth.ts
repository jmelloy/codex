import { defineStore } from "pinia"
import { ref } from "vue"
import { authService, type User } from "../services/auth"
import { useThemeStore } from "./theme"

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null)
  const isAuthenticated = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const response = await authService.login({ username, password })
      localStorage.setItem("access_token", response.access_token)
      isAuthenticated.value = true
      await fetchCurrentUser()
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Login failed"
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser() {
    try {
      user.value = await authService.getCurrentUser()
      isAuthenticated.value = true
      // Load theme from user settings
      const themeStore = useThemeStore()
      themeStore.loadFromUser(user.value.theme_setting)
    } catch (e) {
      logout()
    }
  }

  function logout() {
    authService.logout()
    user.value = null
    isAuthenticated.value = false
  }

  async function initialize() {
    if (authService.isAuthenticated()) {
      await fetchCurrentUser()
    }
  }

  return {
    user,
    isAuthenticated,
    loading,
    error,
    login,
    logout,
    fetchCurrentUser,
    initialize,
  }
})
