<template>
  <div class="min-h-screen flex items-center justify-center graph-paper w-full">
    <div class="notebook-page p-8 rounded-lg shadow-lg w-full max-w-md">
      <h1 class="m-0 mb-2 text-center text-3xl" style="color: var(--notebook-text)">
        {{ title }}
      </h1>
      <p v-if="subtitle" class="subtitle text-center mb-8 text-sm" style="color: var(--pen-gray)">
        {{ subtitle }}
      </p>
      
      <slot></slot>
      
      <div v-if="linkText && linkTo" class="text-center mt-6 text-sm" style="color: var(--pen-gray)">
        {{ linkText }}
        <router-link :to="linkTo" class="no-underline font-medium hover:underline" style="color: var(--notebook-accent)">
          {{ linkLabel }}
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string
  subtitle?: string
  linkText?: string
  linkTo?: string
  linkLabel?: string
}

defineProps<Props>()
</script>
