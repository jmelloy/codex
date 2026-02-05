<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-backdrop" @click.self="handleClose">
      <div class="modal-content-large">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-text-primary m-0">User Settings</h2>
          <button
            @click="handleClose"
            class="p-2 rounded-md hover:bg-bg-tertiary transition-colors"
            aria-label="Close"
          >
            <svg
              class="w-6 h-6 text-text-secondary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>

        <!-- Scrollable Content -->
        <div class="modal-scroll-content">
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

          <!-- Integrations Section -->
          <div
            class="rounded-lg shadow-md p-6 mb-6 border border-border-medium bg-bg-primary/80 backdrop-blur-sm"
          >
            <h3 class="text-xl font-semibold mb-4 text-text-primary">Integrations</h3>
            <p class="mb-6 text-text-secondary">
              Connect Codex to external services and APIs to extend functionality.
            </p>

            <div v-if="integrationsLoading" class="text-text-secondary">
              Loading integrations...
            </div>

            <div v-else-if="integrations.length === 0" class="text-text-secondary">
              No integrations available.
            </div>

            <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                v-for="integration in integrations"
                :key="integration.id"
                @click="configureIntegration(integration.id)"
                class="p-4 rounded-lg border border-border-medium hover:border-primary/50 hover:shadow-sm transition-all cursor-pointer"
              >
                <div class="flex items-start justify-between mb-2">
                  <div class="font-semibold text-text-primary">{{ integration.name }}</div>
                  <span class="text-xs text-text-secondary bg-bg-secondary px-2 py-0.5 rounded">
                    v{{ integration.version }}
                  </span>
                </div>
                <p class="text-sm text-text-secondary mb-3">{{ integration.description }}</p>
                <div class="flex items-center justify-between text-xs">
                  <span class="text-text-secondary">
                    {{ integration.api_type || 'API' }}
                    <span v-if="integration.auth_method"> · {{ integration.auth_method }}</span>
                  </span>
                  <span
                    :class="[
                      'px-2 py-0.5 rounded font-medium',
                      integration.enabled
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-600'
                    ]"
                  >
                    {{ integration.enabled ? 'Enabled' : 'Disabled' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Account Settings Section -->
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
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "../stores/auth"
import { useThemeStore, type ThemeName } from "../stores/theme"
import { useIntegrationStore } from "../stores/integration"

interface Props {
  modelValue: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
}>()

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const integrationStore = useIntegrationStore()

const themeSaved = ref(false)
let themeSavedTimeout: number | null = null

const integrations = computed(() => integrationStore.availableIntegrations)
const integrationsLoading = computed(() => !integrationStore.integrationsLoaded)

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

function configureIntegration(integrationId: string) {
  // Close the modal before navigating
  emit("update:modelValue", false)
  router.push({ name: "integration-config", params: { integrationId } })
}

function handleClose() {
  emit("update:modelValue", false)
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

/* Dark theme uses a lighter overlay for better contrast */
:global(.theme-blueprint) .modal-backdrop {
  background-color: rgba(0, 0, 0, 0.7);
}

.modal-content-large {
  background-color: var(--color-bg-primary);
  padding: 2rem;
  border-radius: 0.5rem;
  width: 100%;
  max-width: 56rem;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--color-border-light);
  opacity: 1;
  isolation: isolate;
}

/* Dark theme modal styling */
:global(.theme-blueprint) .modal-content-large {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
}

.modal-scroll-content {
  overflow-y: auto;
  flex: 1;
  padding-right: 0.5rem;
}

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
