<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary to-purple-600 w-full">
    <div class="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
      <h1 class="m-0 mb-2 text-gray-800 text-center text-3xl">Codex</h1>
      <p class="subtitle text-center text-gray-600 mb-8 text-sm">Laboratory Journal System</p>
      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label for="username" class="block mb-2 text-gray-800 font-medium">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="Enter username"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded text-base focus:outline-none focus:border-primary"
          />
        </div>
        <div class="mb-4">
          <label for="password" class="block mb-2 text-gray-800 font-medium">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Enter password"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded text-base focus:outline-none focus:border-primary"
          />
        </div>
        <div v-if="authStore.error" class="error text-red-600 mb-4 p-2 bg-red-100 rounded text-sm">
          {{ authStore.error }}
        </div>
        <button type="submit" :disabled="authStore.loading" class="w-full px-3 py-2 bg-primary text-white border-none rounded text-base cursor-pointer transition hover:bg-primary-hover disabled:bg-gray-400 disabled:cursor-not-allowed">
          {{ authStore.loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>
      <div class="register-link text-center mt-6 text-gray-600 text-sm">
        Don't have an account? 
        <router-link to="/register" class="text-primary no-underline font-medium hover:underline">Register here</router-link>
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
/* Tailwind classes used, minimal custom styles needed */
</style>
