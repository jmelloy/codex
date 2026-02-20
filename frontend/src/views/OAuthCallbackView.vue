<template>
  <div class="min-h-screen flex items-center justify-center graph-paper w-full">
    <div class="notebook-page p-8 rounded-lg shadow-lg w-full max-w-md text-center">
      <h1 class="m-0 mb-4 text-2xl" style="color: var(--notebook-text)">
        {{ title }}
      </h1>
      <p v-if="loading" class="text-sm" style="color: var(--pen-gray)">
        Connecting your Google account...
      </p>
      <div
        v-if="error"
        class="p-3 rounded text-sm mb-4"
        style="
          color: var(--pen-red);
          background: color-mix(in srgb, var(--pen-red) 10%, transparent);
        "
      >
        {{ error }}
      </div>
      <div
        v-if="success"
        class="p-3 rounded text-sm mb-4"
        style="
          color: var(--pen-green, #2d6a4f);
          background: color-mix(in srgb, var(--pen-green, #2d6a4f) 10%, transparent);
        "
      >
        Successfully connected {{ providerEmail ? `as ${providerEmail}` : "your Google account" }}.
        Redirecting...
      </div>
      <router-link
        v-if="error"
        to="/"
        class="notebook-button inline-block px-4 py-2 border-none rounded text-sm cursor-pointer no-underline mt-2"
      >
        Back to Home
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRouter, useRoute } from "vue-router"
import { oauthService } from "../services/oauth"
import { useAuthStore } from "../stores/auth"
import { authService } from "../services/auth"

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref<string | null>(null)
const success = ref(false)
const providerEmail = ref<string | null>(null)
const title = ref("Connecting Account")

function isLoginFlow(state?: string): boolean {
  if (!state) return false
  try {
    // JWT state tokens are base64-encoded; decode the payload to check mode
    const parts = state.split(".")
    if (parts.length === 3) {
      const payload = JSON.parse(atob(parts[1]))
      return payload.mode === "login"
    }
  } catch {
    // Not a valid JWT — fall through
  }
  return false
}

onMounted(async () => {
  const code = route.query.code as string
  const state = route.query.state as string | undefined
  const errorParam = route.query.error as string | undefined

  if (errorParam) {
    loading.value = false
    error.value = `Authorization denied: ${errorParam}`
    title.value = "Connection Failed"
    return
  }

  if (!code) {
    loading.value = false
    error.value = "No authorization code received"
    title.value = "Connection Failed"
    return
  }

  if (isLoginFlow(state)) {
    // Sign-in / Sign-up flow (unauthenticated)
    try {
      const result = await oauthService.handleGoogleLoginCallback(code, state)
      // Save the JWT token
      authService.saveToken(result.access_token)
      await authStore.fetchCurrentUser()

      success.value = true
      providerEmail.value = result.provider_email
      title.value = "Signed In"
      loading.value = false

      // Redirect to home
      setTimeout(() => {
        router.push("/")
      }, 1000)
    } catch (e: any) {
      loading.value = false
      error.value = e.response?.data?.detail || "Failed to sign in with Google"
      title.value = "Sign-In Failed"
    }
  } else {
    // Connect flow (authenticated — linking Google account)
    try {
      const result = await oauthService.handleGoogleCallback(code, state)
      success.value = true
      providerEmail.value = result.provider_email
      title.value = "Connected"
      loading.value = false

      // Redirect back to calendar view after a short delay
      setTimeout(() => {
        router.push("/calendar")
      }, 1500)
    } catch (e: any) {
      loading.value = false
      error.value = e.response?.data?.detail || "Failed to connect Google account"
      title.value = "Connection Failed"
    }
  }
})
</script>
