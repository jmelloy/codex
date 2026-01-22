<script setup lang="ts">
import { watchEffect } from 'vue'
import { useThemeStore } from './stores/theme'

const themeStore = useThemeStore()

// Apply theme class to document body
watchEffect(() => {
  // Remove any existing theme classes
  document.body.classList.remove('theme-cream', 'theme-manila', 'theme-white', 'theme-blueprint')
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
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
