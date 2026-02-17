<template>
  <button
    type="button"
    class="google-button w-full px-3 py-2 rounded text-sm cursor-pointer border inline-flex items-center justify-center gap-2"
    :disabled="loading"
    @click="handleClick"
  >
    <svg width="18" height="18" viewBox="0 0 48 48">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
    {{ loading ? "Connecting..." : label }}
  </button>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { oauthService } from "../services/oauth"

defineProps<{
  label: string
}>()

const emit = defineEmits<{
  error: [message: string]
}>()

const loading = ref(false)

async function handleClick() {
  loading.value = true
  try {
    const { authorization_url } = await oauthService.getGoogleAuthUrl()
    window.location.href = authorization_url
  } catch (e: any) {
    emit("error", e.response?.data?.detail || "Failed to connect to Google")
    loading.value = false
  }
}
</script>

<style scoped>
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
