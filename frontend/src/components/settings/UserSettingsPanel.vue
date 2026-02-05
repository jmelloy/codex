<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <h1 class="panel-title">User Settings</h1>
      <p class="panel-subtitle">Manage your account and preferences</p>
    </div>

    <div class="panel-content">
      <!-- Theme Configuration -->
      <section class="config-section">
        <h3 class="section-heading">Display Theme</h3>
        <p class="section-description">
          Select your preferred visual theme for the application
        </p>

        <div class="theme-grid">
          <div
            v-for="themeOption in availableThemeOptions"
            :key="themeOption.id"
            @click="applyTheme(themeOption.id)"
            :class="['theme-card', { 'theme-card-selected': currentThemeId === themeOption.id }]">
            <div :class="['theme-preview', themeOption.previewClass]">
              <div class="preview-content">
                <div class="preview-line">{{ themeOption.displayName }}</div>
                <div class="preview-line-dim">Sample content</div>
              </div>
            </div>
            <div class="theme-info">
              <div class="theme-name">{{ themeOption.displayName }}</div>
              <div class="theme-desc">{{ themeOption.details }}</div>
              <div v-if="currentThemeId === themeOption.id" class="active-marker">✓ Active</div>
            </div>
          </div>
        </div>

        <div v-if="themeSaveNotification" class="save-notification">
          Theme applied successfully
        </div>
      </section>

      <!-- Account Information -->
      <section class="config-section">
        <h3 class="section-heading">Account Information</h3>
        <div class="form-field">
          <label class="field-label">Username</label>
          <input
            type="text"
            :value="currentUsername"
            disabled
            class="field-input field-input-disabled"
          />
        </div>
        <p class="info-text">Additional account options coming soon</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore, type ThemeName } from '../../stores/theme'

const authStore = useAuthStore()
const themeStore = useThemeStore()

const themeSaveNotification = ref(false)
let notificationTimer: ReturnType<typeof setTimeout> | null = null

interface ThemeOption {
  id: ThemeName
  displayName: string
  details: string
  previewClass: string
}

const availableThemeOptions = computed<ThemeOption[]>(() => {
  return themeStore.availableThemes.map(t => ({
    id: t.name,
    displayName: t.label,
    details: t.description,
    previewClass: t.className
  }))
})

const currentThemeId = computed(() => themeStore.currentTheme)
const currentUsername = computed(() => authStore.user?.username || '')

function applyTheme(themeId: ThemeName) {
  themeStore.setTheme(themeId)
  
  themeSaveNotification.value = true
  if (notificationTimer) {
    clearTimeout(notificationTimer)
  }
  notificationTimer = setTimeout(() => {
    themeSaveNotification.value = false
  }, 2500)
}
</script>

<style scoped>
.panel-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: 2rem 2.5rem;
  border-bottom: 1px solid var(--color-border-light);
}

.panel-title {
  margin: 0 0 0.5rem;
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.panel-subtitle {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 1rem;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem 2.5rem;
}

.config-section {
  margin-bottom: 3rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-medium);
  border-radius: 8px;
  padding: 2rem;
}

.section-heading {
  margin: 0 0 0.75rem;
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.section-description {
  margin: 0 0 1.75rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}

.theme-card {
  border: 2px solid var(--color-border-light);
  border-radius: 8px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-bg-primary);
}

.theme-card:hover {
  border-color: var(--notebook-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.theme-card-selected {
  border-color: var(--notebook-accent);
  box-shadow: 0 0 0 1px var(--notebook-accent);
}

.theme-preview {
  height: 100px;
  border-radius: 6px;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border-medium);
  overflow: hidden;
}

.preview-content {
  padding: 1rem;
  font-family: monospace;
  font-size: 0.875rem;
}

.preview-line {
  margin-bottom: 0.5rem;
}

.preview-line-dim {
  opacity: 0.7;
}

.theme-info {
  position: relative;
}

.theme-name {
  font-weight: 600;
  font-size: 1.0625rem;
  margin-bottom: 0.375rem;
  color: var(--color-text-primary);
}

.theme-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.active-marker {
  position: absolute;
  top: 0;
  right: 0;
  background: var(--notebook-accent);
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.625rem;
  border-radius: 12px;
}

.save-notification {
  padding: 0.875rem 1.125rem;
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 6px;
  color: #155724;
  font-weight: 500;
  font-size: 0.9375rem;
}

.form-field {
  margin-bottom: 1.5rem;
}

.field-label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
  font-size: 0.9375rem;
}

.field-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 6px;
  font-size: 1rem;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.field-input-disabled {
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.info-text {
  color: var(--color-text-tertiary);
  font-size: 0.9375rem;
  margin: 0;
}

/* Theme preview classes */
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
