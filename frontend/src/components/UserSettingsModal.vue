<template>
  <Teleport to="body">
    <div v-if="modelValue" class="settings-overlay" @click.self="closeModal">
      <div class="settings-dialog">
        <!-- Top bar with title and close -->
        <div class="dialog-header">
          <h2 class="header-title">Settings</h2>
          <button @click="closeModal" class="close-btn" aria-label="Close">
            <svg class="close-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>

        <!-- Sidebar + Content Layout -->
        <div class="dialog-body">
          <!-- Navigation sidebar -->
          <aside class="nav-sidebar">
            <nav class="nav-menu">
              <button
                v-for="tab in settingsTabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                :class="['nav-item', { 'nav-item-selected': activeTab === tab.id }]"
              >
                {{ tab.label }}
              </button>
            </nav>
          </aside>

          <!-- Main content area -->
          <div class="content-panel">
            <!-- User tab content -->
            <div v-if="activeTab === 'user'" class="tab-content">
              <h3 class="section-heading">User Preferences</h3>

              <!-- Theme selection -->
              <section class="settings-section">
                <h4 class="subsection-title">Theme</h4>
                <p class="subsection-description">
                  Choose your preferred theme. The theme will be applied across all notebooks and pages.
                </p>

                <div class="theme-grid">
                  <button
                    v-for="themeOption in themeStore.availableThemes"
                    :key="themeOption.name"
                    @click="changeTheme(themeOption.name)"
                    :class="['theme-card', { 'theme-card-active': themeOption.name === themeStore.currentTheme }]"
                  >
                    <div :class="['theme-preview', themeOption.className]">
                      <div class="preview-text">
                        <div>Sample Text</div>
                        <div class="preview-subtitle">Preview of {{ themeOption.label }}</div>
                      </div>
                    </div>

                    <div class="theme-info">
                      <div>
                        <div class="theme-name">{{ themeOption.label }}</div>
                        <div class="theme-desc">{{ themeOption.description }}</div>
                      </div>
                      <svg v-if="themeOption.name === themeStore.currentTheme" class="check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                      </svg>
                    </div>

                    <div v-if="themeOption.name === themeStore.currentTheme" class="active-badge">Active</div>
                  </button>
                </div>

                <div v-if="showThemeSaved" class="success-message">✓ Theme saved successfully</div>
              </section>

              <!-- Account info -->
              <section class="settings-section">
                <h4 class="subsection-title">Account</h4>
                <div class="form-group">
                  <label class="form-label">Username</label>
                  <input type="text" :value="authStore.user?.username" disabled class="form-input-disabled" />
                </div>
                <p class="info-text">More account settings coming soon...</p>
              </section>
            </div>

            <!-- Workspace tab content -->
            <div v-else-if="activeTab === 'workspace'" class="tab-content">
              <h3 class="section-heading">Workspace Preferences</h3>
              <p class="info-text">Configure workspace-level settings. <a href="/settings/workspace" class="text-link" @click.prevent="navigateToWorkspace">Go to workspace settings →</a></p>
            </div>

            <!-- Notebook tab content -->
            <div v-else-if="activeTab === 'notebook'" class="tab-content">
              <h3 class="section-heading">Notebook Preferences</h3>
              <p class="info-text">Configure notebook-level settings. <a href="/settings/notebook" class="text-link" @click.prevent="navigateToNotebook">Go to notebook settings →</a></p>
            </div>

            <!-- Integrations tab content -->
            <div v-else-if="activeTab === 'integrations'" class="tab-content">
              <h3 class="section-heading">Integrations</h3>
              <p class="subsection-description">Connect Codex to external services and APIs to extend functionality.</p>

              <div v-if="integrationsLoading" class="loading-text">Loading integrations...</div>
              <div v-else-if="integrationList.length === 0" class="empty-text">No integrations available.</div>

              <div v-else class="integration-grid">
                <div
                  v-for="item in integrationList"
                  :key="item.id"
                  @click="openIntegrationConfig(item.id)"
                  class="integration-card"
                >
                  <div class="integration-header">
                    <div class="integration-name">{{ item.name }}</div>
                    <span class="version-badge">v{{ item.version }}</span>
                  </div>
                  <p class="integration-description">{{ item.description }}</p>
                  <div class="integration-footer">
                    <span class="integration-meta">
                      {{ item.api_type || 'API' }}
                      <span v-if="item.auth_method"> · {{ item.auth_method }}</span>
                    </span>
                    <span :class="['status-badge', { 'status-enabled': item.enabled }]">
                      {{ item.enabled ? 'Enabled' : 'Disabled' }}
                    </span>
                  </div>
                </div>
              </div>
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

const routerInstance = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const integrationStore = useIntegrationStore()

const activeTab = ref('user')
const showThemeSaved = ref(false)
let themeTimerId: number | null = null

const settingsTabs = [
  { id: 'user', label: 'User Preferences' },
  { id: 'workspace', label: 'Workspace Preferences' },
  { id: 'notebook', label: 'Notebook Preferences' },
  { id: 'integrations', label: 'Integrations' }
]

const integrationList = computed(() => integrationStore.availableIntegrations)
const integrationsLoading = computed(() => !integrationStore.integrationsLoaded)

function changeTheme(themeName: ThemeName) {
  themeStore.setTheme(themeName)
  showThemeSaved.value = true
  if (themeTimerId) clearTimeout(themeTimerId)
  themeTimerId = setTimeout(() => { showThemeSaved.value = false }, 3000) as unknown as number
}

function openIntegrationConfig(integrationId: string) {
  emit("update:modelValue", false)
  routerInstance.push({ name: "integration-config", params: { integrationId } })
}

function navigateToWorkspace() {
  emit("update:modelValue", false)
  routerInstance.push('/settings/workspace')
}

function navigateToNotebook() {
  emit("update:modelValue", false)
  routerInstance.push('/settings/notebook')
}

function closeModal() {
  emit("update:modelValue", false)
}
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

:global(.theme-blueprint) .settings-overlay {
  background-color: rgba(0, 0, 0, 0.7);
}

.settings-dialog {
  background-color: var(--color-bg-primary);
  border-radius: 0.5rem;
  width: 100%;
  max-width: 64rem;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--color-border-light);
}

:global(.theme-blueprint) .settings-dialog {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--color-border-medium);
}

.header-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.close-btn {
  padding: 0.5rem;
  border-radius: 0.375rem;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: var(--color-bg-tertiary);
}

.close-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: var(--color-text-secondary);
}

.dialog-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.nav-sidebar {
  width: 16rem;
  min-width: 16rem;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border-medium);
  overflow-y: auto;
}

.nav-menu {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-item {
  display: block;
  padding: 0.75rem 1rem;
  border-radius: 0.375rem;
  text-align: left;
  font-size: 0.875rem;
  color: var(--color-text-primary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s;
}

.nav-item:hover:not(.nav-item-selected) {
  background: var(--color-bg-tertiary);
}

.nav-item-selected {
  background: var(--notebook-accent);
  color: var(--color-text-inverse);
  font-weight: 500;
}

.content-panel {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.tab-content {
  max-width: 48rem;
  margin: 0 auto;
}

.section-heading {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 1.5rem 0;
}

.settings-section {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-medium);
  border-radius: 0.5rem;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.subsection-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 1rem 0;
}

.subsection-description {
  margin-bottom: 1.5rem;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1rem;
}

.theme-card {
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 2px solid var(--color-border-light);
  background: transparent;
  text-align: left;
  position: relative;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-card:hover:not(.theme-card-active) {
  border-color: color-mix(in srgb, var(--notebook-accent) 50%, transparent);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.theme-card-active {
  border-color: var(--notebook-accent);
  background: color-mix(in srgb, var(--notebook-accent) 5%, transparent);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.theme-preview {
  width: 100%;
  height: 6rem;
  border-radius: 0.375rem;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border-medium);
  overflow: hidden;
}

.preview-text {
  padding: 0.75rem;
  font-size: 0.875rem;
  font-family: monospace;
}

.preview-subtitle {
  opacity: 0.7;
  margin-top: 0.25rem;
}

.theme-info {
  display: flex;
  align-items: start;
  justify-content: space-between;
}

.theme-name {
  font-weight: 600;
  font-size: 1.125rem;
  color: var(--color-text-primary);
}

.theme-desc {
  font-size: 0.875rem;
  opacity: 0.7;
  margin-top: 0.25rem;
  color: var(--color-text-primary);
}

.check-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: var(--notebook-accent);
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.active-badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: var(--notebook-accent);
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

.success-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--color-success-bg, #d1fae5);
  border: 1px solid var(--color-success-border, #10b981);
  border-radius: 0.375rem;
  color: var(--color-success, #065f46);
  font-size: 0.875rem;
  font-weight: 500;
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
  color: var(--color-text-secondary);
}

.form-input-disabled {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 0.375rem;
  background: var(--color-bg-disabled);
  color: var(--color-text-disabled);
  cursor: not-allowed;
}

.info-text {
  font-size: 0.875rem;
  opacity: 0.7;
  color: var(--color-text-primary);
}

.text-link {
  color: var(--notebook-accent);
  text-decoration: underline;
  cursor: pointer;
}

.text-link:hover {
  opacity: 0.8;
}

.loading-text, .empty-text {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.integration-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1rem;
}

.integration-card {
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border-medium);
  cursor: pointer;
  transition: all 0.2s;
}

.integration-card:hover {
  border-color: color-mix(in srgb, var(--notebook-accent) 50%, transparent);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.integration-header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.integration-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.version-badge {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
}

.integration-description {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.75rem;
}

.integration-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
}

.integration-meta {
  color: var(--color-text-secondary);
}

.status-badge {
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 500;
  background: #f3f4f6;
  color: #6b7280;
}

.status-enabled {
  background: #d1fae5;
  color: #065f46;
}

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
