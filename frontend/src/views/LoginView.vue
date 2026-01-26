<template>
  <BaseAuthLayout
    title="Codex"
    subtitle="Laboratory Journal System"
    link-text="Don't have an account?"
    link-to="/register"
    link-label="Register here"
  >
    <form @submit.prevent="handleLogin">
      <BaseInput
        id="username"
        v-model="username"
        type="text"
        label="Username"
        placeholder="Enter username"
        required
      />
      <BaseInput
        id="password"
        v-model="password"
        type="password"
        label="Password"
        placeholder="Enter password"
        required
      />
      <div v-if="authStore.error" class="error mb-4 p-2 rounded text-sm" style="color: var(--pen-red); background: color-mix(in srgb, var(--pen-red) 10%, transparent)">
        {{ authStore.error }}
      </div>
      <BaseButton
        type="submit"
        variant="primary"
        :disabled="authStore.loading"
        full-width
      >
        {{ authStore.loading ? 'Logging in...' : 'Login' }}
      </BaseButton>
    </form>
  </BaseAuthLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import BaseAuthLayout from '../components/base/BaseAuthLayout.vue'
import BaseInput from '../components/base/BaseInput.vue'
import BaseButton from '../components/base/BaseButton.vue'

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
/* Additional styles if needed */
</style>
