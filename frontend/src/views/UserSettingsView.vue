<template>
  <div class="h-screen flex flex-col w-full">
    <nav class="bg-primary text-white px-8 py-4 flex justify-between items-center">
      <h1 class="text-2xl font-semibold m-0">Codex - User Settings</h1>
      <div class="flex items-center gap-4">
        <button
          @click="goBack"
          class="bg-white/20 text-white border-none px-4 py-2 rounded cursor-pointer hover:bg-white/30 transition"
        >
          ← Back
        </button>
        <span>{{ authStore.user?.username }}</span>
        <button
          @click="handleLogout"
          class="bg-white/20 text-white border-none px-4 py-2 rounded cursor-pointer hover:bg-white/30 transition"
        >
          Logout
        </button>
      </div>
    </nav>

    <div class="flex-1 overflow-auto p-8">
      <div class="max-w-4xl mx-auto">
        <h2 class="text-3xl font-bold mb-6">User Settings</h2>

        <!-- Theme Settings Section -->
        <div
          class="rounded-lg shadow-md p-6 mb-6 border border-border-medium bg-bg-primary/80 backdrop-blur-sm"
        >
          <h3 class="text-xl font-semibold mb-4 text-text-primary">Theme</h3>
          <p class="mb-6 text-text-secondary">
            Choose your preferred theme. The theme will be applied across all notebooks and pages.
          </p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              v-for="theme in themeStore.availableThemes"
              :key="theme.name"
              @click="selectTheme(theme.name)"
              :class="[
                'p-6 rounded-lg border-2 transition-all text-left relative',
                theme.name === themeStore.currentTheme
                  ? 'border-primary bg-primary/5 shadow-md'
                  : 'border-border-light hover:border-primary/50 hover:shadow-sm',
              ]"
            >
              <!-- Theme Preview Box -->
              <div
                :class="[
                  'w-full h-24 rounded-md mb-4 border border-border-medium',
                  theme.className,
                ]"
              >
                <div class="p-3 text-sm font-mono">
                  <div>Sample Text</div>
                  <div class="opacity-70">Preview of {{ theme.label }}</div>
                </div>
              </div>

              <!-- Theme Info -->
              <div class="flex items-start justify-between">
                <div>
                  <div class="font-semibold text-lg">{{ theme.label }}</div>
                  <div class="text-sm opacity-70 mt-1">
                    {{ theme.description }}
                  </div>
                </div>
                <svg
                  v-if="theme.name === themeStore.currentTheme"
                  class="w-6 h-6 text-primary flex-shrink-0 ml-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 13l4 4L19 7"
                  ></path>
                </svg>
              </div>

              <!-- Active Badge -->
              <div
                v-if="theme.name === themeStore.currentTheme"
                class="absolute top-2 right-2 bg-primary text-white text-xs font-semibold px-2 py-1 rounded"
              >
                Active
              </div>
            </button>
          </div>

          <div
            v-if="themeSaved"
            class="mt-4 p-3 bg-success-bg border border-success-border rounded-md text-success text-sm font-medium"
          >
            ✓ Theme saved successfully
          </div>
        </div>

        <!-- Account Settings Section (Placeholder) -->
        <div
          class="rounded-lg shadow-md p-6 border border-border-medium bg-bg-primary/80 backdrop-blur-sm"
        >
          <h3 class="text-xl font-semibold mb-4 text-text-primary">Account</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-1 text-text-secondary">Username</label>
              <input
                type="text"
                :value="authStore.user?.username"
                disabled
                class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-disabled text-text-disabled cursor-not-allowed"
              />
            </div>
            <p class="text-sm opacity-70">More account settings coming soon...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "../stores/auth"
import { useThemeStore, type ThemeName } from "../stores/theme"

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const themeSaved = ref(false)
let themeSavedTimeout: number | null = null

function selectTheme(themeName: ThemeName) {
  themeStore.setTheme(themeName)

  // Show saved message briefly
  themeSaved.value = true
  if (themeSavedTimeout) {
    clearTimeout(themeSavedTimeout)
  }
  themeSavedTimeout = setTimeout(() => {
    themeSaved.value = false
  }, 3000) as unknown as number
}

function goBack() {
  router.push("/")
}

function handleLogout() {
  authStore.logout()
  router.push("/login")
}
</script>

<style scoped>
/* Apply theme-specific styling to the preview boxes */
.theme-cream {
  background-color: var(--page-cream);
  color: var(--pen-black);
}

.theme-manila {
  background-color: var(--page-manila);
  color: var(--pen-black);
}

.theme-white {
  background-color: var(--page-white);
  color: var(--pen-black);
}

.theme-blueprint {
  background-color: var(--page-blueprint);
  color: #e0e7ff;
}
</style>
