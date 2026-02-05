<template>
  <div class="integration-config">
    <div v-if="loading" class="loading-state">
      <p>Loading integration details...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="goBack">Go Back</button>
    </div>

    <div v-else-if="integration" class="config-container">
      <!-- Header -->
      <div class="config-header">
        <button class="back-button" @click="goBack">← Back to Settings</button>
        <h2>{{ integration.name }}</h2>
        <p class="description">{{ integration.description }}</p>
        <div class="meta-info">
          <span class="badge">v{{ integration.version }}</span>
          <span class="badge">{{ integration.api_type }}</span>
          <span class="badge">{{ integration.author }}</span>
        </div>
      </div>

      <!-- Configuration Form -->
      <div class="config-form">
        <h3>Configuration</h3>
        
        <div v-if="!currentWorkspace" class="warning-message">
          <p>⚠️ Please select a workspace first to configure this integration.</p>
        </div>

        <form v-else @submit.prevent="handleSave">
          <!-- Dynamic form fields based on integration properties -->
          <div
            v-for="property in integration.properties"
            :key="property.name"
            class="form-group"
          >
            <label :for="property.name">
              {{ property.ui?.label || formatLabel(property.name) }}
              <span v-if="property.required" class="required">*</span>
            </label>

            <!-- Select/Dropdown (when enum is defined) -->
            <select
              v-if="property.enum && property.enum.length > 0"
              :id="property.name"
              v-model="config[property.name]"
              :required="property.required"
            >
              <option value="" disabled>Select {{ formatLabel(property.name) }}</option>
              <option
                v-for="option in property.enum"
                :key="option"
                :value="option"
              >
                {{ option }}
              </option>
            </select>

            <!-- Number Input -->
            <input
              v-else-if="property.type === 'number' || property.ui?.type === 'number'"
              :id="property.name"
              v-model.number="config[property.name]"
              type="number"
              :min="property.min"
              :max="property.max"
              :placeholder="property.ui?.placeholder"
              :required="property.required"
            />

            <!-- Checkbox (for boolean type) -->
            <label
              v-else-if="property.type === 'boolean' || property.ui?.type === 'checkbox'"
              class="checkbox-label"
            >
              <input
                :id="property.name"
                v-model="config[property.name]"
                type="checkbox"
              />
              {{ property.ui?.label || formatLabel(property.name) }}
            </label>

            <!-- Password Input (for secure fields) -->
            <input
              v-else-if="property.secure"
              :id="property.name"
              v-model="config[property.name]"
              type="password"
              :placeholder="property.ui?.placeholder || 'Enter ' + formatLabel(property.name)"
              :required="property.required"
              autocomplete="off"
            />

            <!-- Default Text Input -->
            <input
              v-else
              :id="property.name"
              v-model="config[property.name]"
              type="text"
              :placeholder="property.ui?.placeholder || 'Enter ' + formatLabel(property.name)"
              :required="property.required"
            />

            <!-- Help text -->
            <small v-if="property.ui?.help || property.description" class="help-text">
              {{ property.ui?.help || property.description }}
            </small>
          </div>

          <!-- Action Buttons -->
          <div class="form-actions">
            <button
              type="button"
              class="btn-secondary"
              @click="handleTest"
              :disabled="testing || saving"
            >
              {{ testing ? 'Testing...' : 'Test Connection' }}
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="saving || testing"
            >
              {{ saving ? 'Saving...' : 'Save Configuration' }}
            </button>
          </div>

          <!-- Test Result -->
          <div
            v-if="testResult"
            class="result-message"
            :class="testResult.success ? 'success' : 'error'"
          >
            <p>{{ testResult.message }}</p>
            <div v-if="testResult.details" class="result-details">
              <pre>{{ JSON.stringify(testResult.details, null, 2) }}</pre>
            </div>
          </div>
        </form>
      </div>

      <!-- Additional Information -->
      <div v-if="integration.blocks && integration.blocks.length > 0" class="info-section">
        <h3>Available Blocks</h3>
        <div class="blocks-list">
          <div v-for="block in integration.blocks" :key="block.id" class="block-item">
            <span class="block-icon">{{ block.icon || '📦' }}</span>
            <div class="block-info">
              <strong>{{ block.name }}</strong>
              <p>{{ block.description }}</p>
              <code v-if="block.syntax">{{ block.syntax }}</code>
            </div>
          </div>
        </div>
      </div>

      <div v-if="integration.endpoints && integration.endpoints.length > 0" class="info-section">
        <h3>Available Endpoints</h3>
        <div class="endpoints-list">
          <div v-for="endpoint in integration.endpoints" :key="endpoint.id" class="endpoint-item">
            <div class="endpoint-header">
              <span class="method">{{ endpoint.method }}</span>
              <code>{{ endpoint.path }}</code>
            </div>
            <p>{{ endpoint.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkspaceStore } from '../stores/workspace'
import {
  getIntegration,
  getIntegrationConfig,
  updateIntegrationConfig,
  testIntegrationConnection,
  type IntegrationDetails,
  type IntegrationTestResult,
} from '../services/integration'

const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()

const integration = ref<IntegrationDetails | null>(null)
const config = ref<Record<string, any>>({})
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const error = ref<string | null>(null)
const testResult = ref<IntegrationTestResult | null>(null)

const integrationId = computed(() => route.params.integrationId as string)
const currentWorkspace = computed(() => workspaceStore.currentWorkspace)

// Helper to get notebook ID for integration operations
// Uses current notebook or falls back to first notebook
function getNotebookId(): number | undefined {
  if (workspaceStore.currentNotebook) {
    return workspaceStore.currentNotebook.id
  } else if (workspaceStore.notebooks.length > 0) {
    return workspaceStore.notebooks[0]?.id
  }
  return undefined
}

// Convert snake_case to Title Case
function formatLabel(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

async function loadIntegration() {
  loading.value = true
  error.value = null

  try {
    // Load integration details
    integration.value = await getIntegration(integrationId.value)

    // Initialize config with defaults
    if (integration.value.properties) {
      integration.value.properties.forEach((prop) => {
        if (prop.default !== undefined) {
          config.value[prop.name] = prop.default
        }
      })
    }

    // Load existing config if workspace is available
    if (currentWorkspace.value?.id) {
      const notebookId = getNotebookId()
      
      if (notebookId) {
        const existingConfig = await getIntegrationConfig(
          integrationId.value,
          currentWorkspace.value.id,
          notebookId
        )
        if (existingConfig.config) {
          config.value = { ...config.value, ...existingConfig.config }
        }
      }
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load integration'
    console.error('Error loading integration:', err)
  } finally {
    loading.value = false
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null

  try {
    const result = await testIntegrationConnection(integrationId.value, config.value)
    testResult.value = result
  } catch (err: any) {
    testResult.value = {
      success: false,
      message: err.message || 'Connection test failed',
    }
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  if (!currentWorkspace.value?.id) {
    testResult.value = {
      success: false,
      message: 'No workspace selected',
    }
    return
  }

  const notebookId = getNotebookId()
  
  if (!notebookId) {
    testResult.value = {
      success: false,
      message: 'No notebook available - please create a notebook first',
    }
    return
  }

  saving.value = true
  testResult.value = null

  try {
    await updateIntegrationConfig(
      integrationId.value,
      currentWorkspace.value.id,
      notebookId,
      config.value
    )
    testResult.value = {
      success: true,
      message: 'Configuration saved successfully!',
    }
  } catch (err: any) {
    testResult.value = {
      success: false,
      message: err.message || 'Failed to save configuration',
    }
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push({ name: 'settings' })
}

onMounted(() => {
  loadIntegration()
})
</script>

<style scoped>
.integration-config {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}

.error-state button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: var(--notebook-accent);
  color: var(--color-text-inverse);
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.error-state button:hover {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.config-header {
  margin-bottom: 2rem;
}

.back-button {
  background: none;
  border: none;
  color: var(--notebook-accent);
  cursor: pointer;
  font-size: 1rem;
  padding: 0.5rem 0;
  margin-bottom: 1rem;
}

.back-button:hover {
  text-decoration: underline;
}

.config-header h2 {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.description {
  color: var(--color-text-secondary);
  font-size: 1rem;
  margin-bottom: 1rem;
}

.meta-info {
  display: flex;
  gap: 0.5rem;
}

.badge {
  background: var(--color-bg-tertiary);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.warning-message {
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  color: var(--color-warning);
}

.config-form,
.info-section {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-medium);
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 1.5rem;
}

.config-form h3,
.info-section h3 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: var(--color-text-primary);
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
}

.required {
  color: var(--color-error);
  margin-left: 0.25rem;
}

.form-group input[type='text'],
.form-group input[type='password'],
.form-group input[type='number'],
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  font-size: 1rem;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--notebook-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--notebook-accent) 15%, transparent);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  color: var(--color-text-primary);
}

.checkbox-label input[type='checkbox'] {
  width: auto;
}

.help-text {
  display: block;
  margin-top: 0.5rem;
  color: var(--color-text-tertiary);
  font-size: 0.875rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--notebook-accent);
  color: var(--color-text-inverse);
}

.btn-primary:hover:not(:disabled) {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.btn-secondary {
  background: var(--color-text-tertiary);
  color: var(--color-text-inverse);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-text-secondary);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-message {
  margin-top: 1.5rem;
  padding: 1rem;
  border-radius: 4px;
}

.result-message.success {
  background: var(--color-success-bg);
  border: 1px solid var(--color-success-border);
  color: var(--color-success);
}

.result-message.error {
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  color: var(--color-error);
}

.result-details {
  margin-top: 0.5rem;
  background: color-mix(in srgb, var(--color-text-primary) 5%, transparent);
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.result-details pre {
  margin: 0;
  white-space: pre-wrap;
  color: var(--color-text-primary);
}

.blocks-list,
.endpoints-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.block-item,
.endpoint-item {
  padding: 1rem;
  background: var(--color-bg-secondary);
  border-radius: 4px;
}

.block-item {
  display: flex;
  gap: 1rem;
}

.block-icon {
  font-size: 2rem;
}

.block-info {
  flex: 1;
}

.block-info strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--color-text-primary);
}

.block-info p {
  color: var(--color-text-secondary);
  margin: 0.5rem 0;
}

.block-info code {
  display: block;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.endpoint-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.method {
  background: var(--notebook-accent);
  color: var(--color-text-inverse);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.endpoint-item code {
  background: var(--color-bg-primary);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--color-border-medium);
  color: var(--color-text-primary);
}

.endpoint-item p {
  color: var(--color-text-secondary);
  margin: 0;
}
</style>
