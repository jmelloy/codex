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

      <GoogleAuthButton label="Sign up with Google" mode="login" @error="error = $event" />

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
import { useAuthStore } from "../stores/auth"
import { validatePassword, validateUsername, validatePasswordsMatch } from "../utils/validation"
import GoogleAuthButton from "../components/GoogleAuthButton.vue"

const router = useRouter()
const authStore = useAuthStore()

const form = ref({
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
})

const loading = ref(false)
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
</style>
