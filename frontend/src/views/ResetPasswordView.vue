<template>
  <div class="min-h-screen flex items-center justify-center graph-paper w-full">
    <div class="notebook-page p-8 rounded-lg shadow-lg w-full max-w-md">
      <h1 class="m-0 mb-2 text-center text-3xl" style="color: var(--notebook-text)">Reset Password</h1>
      <p class="subtitle text-center mb-8 text-sm" style="color: var(--pen-gray)">
        Enter your new password
      </p>

      <div v-if="!token" class="error mb-4 p-2 rounded text-sm"
        style="color: var(--pen-red); background: color-mix(in srgb, var(--pen-red) 10%, transparent)">
        Missing reset token. Please use the link from your email or contact an administrator.
      </div>

      <form v-else-if="!success" @submit.prevent="handleReset">
        <div class="mb-4">
          <label for="password" class="block mb-2 font-medium" style="color: var(--notebook-text)">New Password</label>
          <input
            id="password"
            v-model="newPassword"
            type="password"
            placeholder="Enter new password (min 8 characters)"
            required
            minlength="8"
            :disabled="loading"
            class="auth-input w-full px-3 py-2 rounded text-base focus:outline-none"
          />
        </div>
        <div class="mb-4">
          <label for="confirmPassword" class="block mb-2 font-medium" style="color: var(--notebook-text)">Confirm Password</label>
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            placeholder="Confirm new password"
            required
            :disabled="loading"
            class="auth-input w-full px-3 py-2 rounded text-base focus:outline-none"
          />
        </div>
        <div
          v-if="error"
          class="error mb-4 p-2 rounded text-sm"
          style="color: var(--pen-red); background: color-mix(in srgb, var(--pen-red) 10%, transparent)"
        >
          {{ error }}
        </div>
        <button
          type="submit"
          :disabled="loading"
          class="notebook-button w-full px-3 py-2 border-none rounded text-base cursor-pointer transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ loading ? "Resetting..." : "Reset Password" }}
        </button>
      </form>

      <div v-else class="success-message p-4 rounded text-sm" style="color: var(--pen-gray)">
        <p class="mb-2 font-medium" style="color: var(--notebook-text)">Password reset successfully</p>
        <p>You can now log in with your new password.</p>
      </div>

      <div class="text-center mt-6 text-sm" style="color: var(--pen-gray)">
        <router-link
          to="/login"
          class="no-underline font-medium hover:underline"
          style="color: var(--notebook-accent)"
        >Back to Login</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import { authService } from "../services/auth"
import { validatePassword, validatePasswordsMatch } from "../utils/validation"

const route = useRoute()

const token = ref("")
const newPassword = ref("")
const confirmPassword = ref("")
const loading = ref(false)
const error = ref("")
const success = ref(false)

onMounted(() => {
  token.value = (route.query.token as string) || ""
})

async function handleReset() {
  error.value = ""

  const pwValid = validatePassword(newPassword.value)
  if (!pwValid.valid) {
    error.value = pwValid.error!
    return
  }

  const matchValid = validatePasswordsMatch(newPassword.value, confirmPassword.value)
  if (!matchValid.valid) {
    error.value = matchValid.error!
    return
  }

  loading.value = true
  try {
    await authService.resetPassword(token.value, newPassword.value)
    success.value = true
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to reset password. The token may be expired."
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
</style>
