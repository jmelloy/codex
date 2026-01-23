<template>
  <div class="min-h-screen flex items-center justify-center graph-paper w-full">
    <div class="notebook-page p-8 rounded-lg shadow-lg w-full max-w-md">
      <h1 class="m-0 mb-2 text-center text-3xl" style="color: var(--notebook-text)">Codex</h1>
      <p class="subtitle text-center mb-8 text-sm" style="color: var(--pen-gray)">Laboratory Journal System</p>
      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label for="username" class="block mb-2 font-medium" style="color: var(--notebook-text)">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="Enter username"
            required
            class="auth-input w-full px-3 py-2 rounded text-base focus:outline-none"
          />
        </div>
        <div class="mb-4">
          <label for="password" class="block mb-2 font-medium" style="color: var(--notebook-text)">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Enter password"
            required
            class="auth-input w-full px-3 py-2 rounded text-base focus:outline-none"
          />
        </div>
        <div v-if="authStore.error" class="error mb-4 p-2 rounded text-sm" style="color: var(--pen-red); background: color-mix(in srgb, var(--pen-red) 10%, transparent)">
          {{ authStore.error }}
        </div>
        <button type="submit" :disabled="authStore.loading" class="notebook-button w-full px-3 py-2 border-none rounded text-base cursor-pointer transition disabled:opacity-50 disabled:cursor-not-allowed">
          {{ authStore.loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>
      <div class="register-link text-center mt-6 text-sm" style="color: var(--pen-gray)">
        Don't have an account? 
        <router-link to="/register" class="no-underline font-medium hover:underline" style="color: var(--notebook-accent)">Register here</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const password = ref('')

async function handleLogin() {
  try {
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    // Error is handled in the store
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
