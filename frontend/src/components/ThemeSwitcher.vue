<template>
  <div class="theme-switcher">
    <button
      @click="toggleDropdown"
      class="theme-button"
      :title="`Current theme: ${themeStore.theme.label}`"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path>
      </svg>
      <span class="theme-label">{{ themeStore.theme.label }}</span>
    </button>

    <div v-if="isOpen" class="theme-dropdown">
      <button
        v-for="theme in themeStore.availableThemes"
        :key="theme.name"
        @click="selectTheme(theme.name)"
        class="theme-option"
        :class="{ active: theme.name === themeStore.currentTheme }"
      >
        <div class="theme-option-content">
          <span class="theme-option-label">{{ theme.label }}</span>
          <span class="theme-option-description">{{ theme.description }}</span>
        </div>
        <span v-if="theme.name === themeStore.currentTheme" class="check-mark">✓</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue"
import { useThemeStore, type ThemeName } from "../stores/theme"

const themeStore = useThemeStore()
const isOpen = ref(false)

function toggleDropdown() {
  isOpen.value = !isOpen.value
}

function selectTheme(themeName: ThemeName) {
  themeStore.setTheme(themeName)
  isOpen.value = false
}

function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest(".theme-switcher")) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside)
})
</script>

<style scoped>
.theme-switcher {
  position: relative;
  display: inline-block;
}

.theme-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: color-mix(in srgb, var(--notebook-text) 8%, transparent);
  border: 1px solid var(--page-border);
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
  color: var(--notebook-text);
}

.theme-button:hover {
  background: color-mix(in srgb, var(--notebook-text) 12%, transparent);
  border-color: var(--page-border);
}

.theme-label {
  font-weight: 500;
}

.theme-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  min-width: 250px;
  background: var(--notebook-bg);
  border: 1px solid var(--page-border);
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px var(--page-shadow);
  overflow: hidden;
  z-index: 1000;
}

.theme-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--notebook-bg);
  border: none;
  border-bottom: 1px solid var(--page-border);
  cursor: pointer;
  text-align: left;
  transition: background 0.2s;
  color: var(--notebook-text);
}

.theme-option:last-child {
  border-bottom: none;
}

.theme-option:hover {
  background: color-mix(in srgb, var(--notebook-accent) 10%, transparent);
}

.theme-option.active {
  background: color-mix(in srgb, var(--notebook-accent) 15%, transparent);
}

.theme-option-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.theme-option-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--notebook-text);
}

.theme-option-description {
  font-size: 0.75rem;
  color: var(--pen-gray);
}

.check-mark {
  font-size: 1rem;
  color: var(--notebook-accent);
  font-weight: bold;
}
</style>
