<template>
  <div class="min-h-screen flex items-center justify-center graph-paper w-full">
    <div class="notebook-page p-8 rounded-lg shadow-lg w-full max-w-md">
      <h1 class="m-0 mb-2 text-center text-3xl" style="color: var(--notebook-text)">Register</h1>
      <p class="subtitle text-center mb-8 text-sm" style="color: var(--pen-gray)">
        Create your account
      </p>
      <form @submit.prevent="handleRegister">
        <div class="mb-4">
          <label for="username" class="block mb-2 font-medium" style="color: var(--notebook-text)"
            >Username</label
          >
          <input
            id="username"
            v-model="form.username"
            type="text"
            required
            minlength="3"
            maxlength="50"
            placeholder="Enter username"
            :disabled="loading"
            class="auth-input w-full px-3 py-2 rounded text-base disabled:cursor-not-allowed focus:outline-none"
          />
        </div>

        <div class="mb-4">
          <label for="email" class="block mb-2 font-medium" style="color: var(--notebook-text)"
            >Email</label
          >
          <input
            id="email"
            v-model="form.email"
            type="email"
            required
            placeholder="Enter email"
            :disabled="loading"
            class="auth-input w-full px-3 py-2 rounded text-base disabled:cursor-not-allowed focus:outline-none"
          />
        </div>

        <div class="mb-4">
          <label for="password" class="block mb-2 font-medium" style="color: var(--notebook-text)"
            >Password</label
          >
          <input
            id="password"
            v-model="form.password"
            type="password"
            required
            minlength="8"
            placeholder="Enter password (min 8 characters)"
            :disabled="loading"
            class="auth-input w-full px-3 py-2 rounded text-base disabled:cursor-not-allowed focus:outline-none"
          />
        </div>

        <div class="mb-4">
          <label
            for="confirmPassword"
            class="block mb-2 font-medium"
            style="color: var(--notebook-text)"
            >Confirm Password</label
          >
          <input
            id="confirmPassword"
            v-model="form.confirmPassword"
            type="password"
            required
            placeholder="Confirm password"
            :disabled="loading"
            class="auth-input w-full px-3 py-2 rounded text-base disabled:cursor-not-allowed focus:outline-none"
          />
        </div>

        <div
          v-if="error"
          class="error mb-4 p-2 rounded text-sm"
          style="
            color: var(--pen-red);
            background: color-mix(in srgb, var(--pen-red) 10%, transparent);
          "
        >
          {{ error }}
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="notebook-button w-full px-3 py-2 border-none rounded text-base cursor-pointer transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ loading ? "Registering..." : "Register" }}
        </button>
      </form>

      <div class="divider flex items-center my-6">
        <span class="flex-1 h-px" style="background: var(--page-border)"></span>
        <span class="px-3 text-xs" style="color: var(--pen-gray)">or</span>
        <span class="flex-1 h-px" style="background: var(--page-border)"></span>
      </div>

      <button
        type="button"
        class="google-button w-full px-3 py-2 rounded text-sm cursor-pointer border inline-flex items-center justify-center gap-2"
        :disabled="googleLoading"
        @click="handleGoogleRegister"
      >
        <svg width="18" height="18" viewBox="0 0 48 48">
          <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
          <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
          <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
          <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
        </svg>
        {{ googleLoading ? "Connecting..." : "Sign up with Google" }}
      </button>

      <div class="login-link text-center mt-6 text-sm" style="color: var(--pen-gray)">
        Already have an account?
        <router-link
          to="/login"
          class="no-underline font-medium hover:underline"
          style="color: var(--notebook-accent)"
          >Login here</router-link
        >
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"
import { authService } from "../services/auth"
import { oauthService } from "../services/oauth"
import { useAuthStore } from "../stores/auth"
import { validatePassword, validateUsername, validatePasswordsMatch } from "../utils/validation"

const router = useRouter()
const authStore = useAuthStore()

const form = ref({
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
})

const loading = ref(false)
const googleLoading = ref(false)
const error = ref("")

const handleRegister = async () => {
  error.value = ""

  // Validate username
  const usernameValidation = validateUsername(form.value.username)
  if (!usernameValidation.valid) {
    error.value = usernameValidation.error || "Invalid username"
    return
  }

  // Validate password
  const passwordValidation = validatePassword(form.value.password)
  if (!passwordValidation.valid) {
    error.value = passwordValidation.error || "Invalid password"
    return
  }

  // Validate passwords match
  const passwordsMatchValidation = validatePasswordsMatch(
    form.value.password,
    form.value.confirmPassword
  )
  if (!passwordsMatchValidation.valid) {
    error.value = passwordsMatchValidation.error || "Passwords do not match"
    return
  }

  loading.value = true

  try {
    // Register the user
    await authService.register({
      username: form.value.username,
      email: form.value.email,
      password: form.value.password,
    })

    // Automatically log in after successful registration
    const tokenResponse = await authService.login({
      username: form.value.username,
      password: form.value.password,
    })

    authService.saveToken(tokenResponse.access_token)
    await authStore.fetchCurrentUser()

    // Redirect to home
    router.push("/")
  } catch (err: any) {
    console.error("Registration error:", err)
    error.value = err.response?.data?.detail || "Registration failed. Please try again."
  } finally {
    loading.value = false
  }
}

async function handleGoogleRegister() {
  googleLoading.value = true
  try {
    const { authorization_url } = await oauthService.getGoogleAuthUrl()
    window.location.href = authorization_url
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to connect to Google"
    googleLoading.value = false
  }
}
</script>

<style scoped>
.auth-input {
  border: 1px solid var(--page-border);
  background: var(--notebook-bg);
  color: var(--notebook-text);
}

.auth-input:focus {
  border-color: var(--notebook-accent);
}

.auth-input::placeholder {
  color: color-mix(in srgb, var(--notebook-text) 40%, transparent);
}

.auth-input:disabled {
  opacity: 0.6;
  background: color-mix(in srgb, var(--notebook-text) 5%, transparent);
}

.google-button {
  background: #fff;
  color: #3c4043;
  border-color: #dadce0;
  font-weight: 500;
  transition: background 0.2s, box-shadow 0.2s;
}

.google-button:hover:not(:disabled) {
  background: #f8f9fa;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.google-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
