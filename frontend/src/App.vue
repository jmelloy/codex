<script setup lang="ts">
import { watchEffect } from "vue"
import { useThemeStore } from "./stores/theme"

const themeStore = useThemeStore()

// Apply theme class to document body
watchEffect(() => {
  // Remove any existing theme-* classes (supports plugin themes)
  const themeClasses = Array.from(document.body.classList).filter(c => c.startsWith("theme-"))
  themeClasses.forEach(c => document.body.classList.remove(c))
  // Add current theme class
  document.body.classList.add(themeStore.theme.className)
})
</script>

<template>
  <div class="w-full h-screen" :class="themeStore.theme.className">
    <router-view />
  </div>
</template>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--notebook-bg);
  color: var(--color-text-primary);
}
</style>
