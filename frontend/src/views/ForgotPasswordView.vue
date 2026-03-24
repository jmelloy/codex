<template>
  <div class="min-h-screen flex items-center justify-center graph-paper w-full">
    <div class="notebook-page p-8 rounded-lg shadow-lg w-full max-w-md">
      <h1 class="m-0 mb-2 text-center text-3xl" style="color: var(--notebook-text)">Forgot Password</h1>
      <p class="subtitle text-center mb-8 text-sm" style="color: var(--pen-gray)">
        Enter your email to receive a reset link
      </p>

      <form v-if="!submitted" @submit.prevent="handleSubmit">
        <div class="mb-4">
          <label for="email" class="block mb-2 font-medium" style="color: var(--notebook-text)">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="Enter your email"
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
          {{ loading ? "Sending..." : "Send Reset Link" }}
        </button>
      </form>

      <div v-else class="success-message p-4 rounded text-sm" style="color: var(--pen-gray)">
        <p class="mb-2 font-medium" style="color: var(--notebook-text)">Check your email</p>
        <p>{{ message }}</p>
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
import { ref } from "vue"
import { authService } from "../services/auth"

const email = ref("")
const loading = ref(false)
const error = ref("")
const submitted = ref(false)
const message = ref("")

async function handleSubmit() {
  error.value = ""
  loading.value = true
  try {
    const result = await authService.forgotPassword(email.value)
    message.value = result.message
    submitted.value = true
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Something went wrong. Please try again."
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
