<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <h1 class="panel-title">Integration Plugins</h1>
      <p class="panel-subtitle">Connect to external services</p>
    </div>

    <div class="panel-content">
      <div v-if="integrationsLoading" class="loading-state">Loading integrations...</div>
      <div v-else-if="integrationsList.length === 0" class="empty-state">
        No integration plugins available
      </div>
      <div v-else class="integrations-list">
        <div 
          v-for="integration in integrationsList" 
          :key="integration.id"
          :class="['integration-card', { 'integration-card-expanded': expandedIntegrationId === integration.id }]">
          
          <!-- Card Header - Always Visible -->
          <div class="card-header" @click="toggleCard(integration.id)">
            <div class="header-main">
              <div class="header-title-row">
                <h3 class="integration-title">{{ integration.name }}</h3>
                <span class="integration-version">v{{ integration.version }}</span>
              </div>
              <p class="integration-description">{{ integration.description }}</p>
              <div class="integration-meta-row">
                <span class="meta-chip">{{ integration.api_type }}</span>
                <span v-if="integration.auth_method" class="meta-chip">{{ integration.auth_method }}</span>
                <span class="meta-chip">{{ integration.author }}</span>
              </div>
            </div>
            <div class="header-controls" @click.stop>
              <label class="toggle-switch-label">
                <input
                  type="checkbox"
                  :checked="integration.enabled"
                  @change="toggleIntegration(integration.id, $event)"
                  class="toggle-checkbox"
                />
                <span class="toggle-slider"></span>
              </label>
              <button 
                @click.stop="toggleCard(integration.id)" 
                class="expand-btn"
                :aria-label="expandedIntegrationId === integration.id ? 'Collapse' : 'Configure'">
                <span v-if="expandedIntegrationId === integration.id">▼</span>
                <span v-else>▶</span>
              </button>
            </div>
          </div>

          <!-- Configuration Panel - Shown When Expanded -->
          <div v-if="expandedIntegrationId === integration.id" class="card-config">
            <div v-if="loadingDetails" class="config-loading">Loading configuration...</div>
            <div v-else-if="configError" class="config-error">
              <p>{{ configError }}</p>
              <button @click="loadIntegrationDetails(integration.id)" class="retry-btn">Retry</button>
            </div>
            <div v-else-if="integrationDetails" class="config-content">
              <!-- Configuration Form -->
              <div v-if="!currentWorkspaceId" class="warning-box">
                ⚠️ Please select a workspace to configure this integration
              </div>
              <form v-else @submit.prevent="saveConfiguration" class="config-form">
                <h4 class="config-section-title">Configuration</h4>
                
                <div v-if="!integrationDetails.properties || integrationDetails.properties.length === 0" class="no-config">
                  No configuration options available
                </div>
                
                <div v-else class="form-fields">
                  <div
                    v-for="prop in integrationDetails.properties"
                    :key="prop.name"
                    class="form-field">
                    <label :for="`${integration.id}-${prop.name}`" class="field-label">
                      {{ prop.ui?.label || formatPropertyName(prop.name) }}
                      <span v-if="prop.required" class="required-mark">*</span>
                    </label>

                    <!-- Select dropdown -->
                    <select
                      v-if="prop.enum && prop.enum.length > 0"
                      :id="`${integration.id}-${prop.name}`"
                      v-model="configData[prop.name]"
                      :required="prop.required"
                      class="field-input">
                      <option value="" disabled>Select {{ formatPropertyName(prop.name) }}</option>
                      <option v-for="opt in prop.enum" :key="opt" :value="opt">{{ opt }}</option>
                    </select>

                    <!-- Number input -->
                    <input
                      v-else-if="prop.type === 'number' || prop.ui?.type === 'number'"
                      :id="`${integration.id}-${prop.name}`"
                      v-model.number="configData[prop.name]"
                      type="number"
                      :min="prop.min"
                      :max="prop.max"
                      :placeholder="prop.ui?.placeholder"
                      :required="prop.required"
                      class="field-input"
                    />

                    <!-- Checkbox -->
                    <label
                      v-else-if="prop.type === 'boolean' || prop.ui?.type === 'checkbox'"
                      class="checkbox-field">
                      <input
                        :id="`${integration.id}-${prop.name}`"
                        v-model="configData[prop.name]"
                        type="checkbox"
                        class="field-checkbox"
                      />
                      <span>{{ prop.ui?.label || formatPropertyName(prop.name) }}</span>
                    </label>

                    <!-- Password input -->
                    <input
                      v-else-if="prop.secure"
                      :id="`${integration.id}-${prop.name}`"
                      v-model="configData[prop.name]"
                      type="password"
                      :placeholder="prop.ui?.placeholder || `Enter ${formatPropertyName(prop.name)}`"
                      :required="prop.required"
                      autocomplete="off"
                      class="field-input"
                    />

                    <!-- Text input -->
                    <input
                      v-else
                      :id="`${integration.id}-${prop.name}`"
                      v-model="configData[prop.name]"
                      type="text"
                      :placeholder="prop.ui?.placeholder || `Enter ${formatPropertyName(prop.name)}`"
                      :required="prop.required"
                      class="field-input"
                    />

                    <small v-if="prop.ui?.help || prop.description" class="field-help">
                      {{ prop.ui?.help || prop.description }}
                    </small>
                  </div>
                </div>

                <!-- Action Buttons -->
                <div class="form-actions">
                  <button
                    type="button"
                    @click="testConfiguration"
                    :disabled="isTesting || isSaving"
                    class="btn-test">
                    {{ isTesting ? 'Testing...' : 'Test Connection' }}
                  </button>
                  <button
                    type="submit"
                    :disabled="isSaving || isTesting"
                    class="btn-save">
                    {{ isSaving ? 'Saving...' : 'Save Configuration' }}
                  </button>
                </div>

                <!-- Result Messages -->
                <div v-if="testResultMsg" :class="['result-box', testResultMsg.success ? 'result-success' : 'result-error']">
                  <p>{{ testResultMsg.message }}</p>
                  <pre v-if="testResultMsg.details" class="result-details">{{ JSON.stringify(testResultMsg.details, null, 2) }}</pre>
                </div>
              </form>

              <!-- Additional Info Sections -->
              <div v-if="integrationDetails.blocks && integrationDetails.blocks.length > 0" class="info-section">
                <h4 class="info-section-title">Available Blocks</h4>
                <div class="blocks-grid">
                  <div v-for="block in integrationDetails.blocks" :key="block.id" class="block-card">
                    <span class="block-icon">{{ block.icon || '📦' }}</span>
                    <div class="block-content">
                      <strong class="block-name">{{ block.name }}</strong>
                      <p class="block-desc">{{ block.description }}</p>
                      <code v-if="block.syntax" class="block-syntax">{{ block.syntax }}</code>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="integrationDetails.endpoints && integrationDetails.endpoints.length > 0" class="info-section">
                <h4 class="info-section-title">Available Endpoints</h4>
                <div class="endpoints-list">
                  <div v-for="endpoint in integrationDetails.endpoints" :key="endpoint.id" class="endpoint-card">
                    <div class="endpoint-header">
                      <span class="endpoint-method">{{ endpoint.method }}</span>
                      <code class="endpoint-path">{{ endpoint.path }}</code>
                    </div>
                    <p class="endpoint-desc">{{ endpoint.description }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useIntegrationStore } from '../../stores/integration'
import { useWorkspaceStore } from '../../stores/workspace'
import {
  getIntegration,
  getIntegrationConfig,
  updateIntegrationConfig,
  testIntegrationConnection,
  type IntegrationDetails,
  type IntegrationTestResult,
} from '../../services/integration'

const integrationStore = useIntegrationStore()
const workspaceStore = useWorkspaceStore()

const expandedIntegrationId = ref<string | null>(null)
const integrationDetails = ref<IntegrationDetails | null>(null)
const configData = ref<Record<string, any>>({})
const loadingDetails = ref(false)
const configError = ref<string | null>(null)
const isSaving = ref(false)
const isTesting = ref(false)
const testResultMsg = ref<IntegrationTestResult | null>(null)

const integrationsList = computed(() => integrationStore.availableIntegrations)
const integrationsLoading = computed(() => !integrationStore.integrationsLoaded)
const currentWorkspaceId = computed(() => workspaceStore.currentWorkspace?.id)
const currentNotebookId = computed(() => workspaceStore.currentNotebook?.id || workspaceStore.notebooks[0]?.id)

function formatPropertyName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

async function toggleCard(integrationId: string) {
  if (expandedIntegrationId.value === integrationId) {
    expandedIntegrationId.value = null
    integrationDetails.value = null
    configData.value = {}
    testResultMsg.value = null
  } else {
    expandedIntegrationId.value = integrationId
    await loadIntegrationDetails(integrationId)
  }
}

async function loadIntegrationDetails(integrationId: string) {
  loadingDetails.value = true
  configError.value = null
  
  try {
    // Load integration details
    integrationDetails.value = await getIntegration(integrationId)
    
    // Initialize config with defaults
    if (integrationDetails.value.properties) {
      integrationDetails.value.properties.forEach((prop) => {
        if (prop.default !== undefined) {
          configData.value[prop.name] = prop.default
        }
      })
    }
    
    // Load existing configuration if workspace available
    if (currentWorkspaceId.value && currentNotebookId.value) {
      try {
        const existingConfig = await getIntegrationConfig(
          integrationId,
          currentWorkspaceId.value,
          currentNotebookId.value
        )
        if (existingConfig.config) {
          configData.value = { ...configData.value, ...existingConfig.config }
        }
      } catch (err) {
        // Config might not exist yet, that's ok
        console.log('No existing config found, using defaults')
      }
    }
  } catch (err: any) {
    configError.value = err.message || 'Failed to load integration details'
    console.error('Error loading integration details:', err)
  } finally {
    loadingDetails.value = false
  }
}

async function toggleIntegration(integrationId: string, event: Event) {
  const checkbox = event.target as HTMLInputElement
  const newState = checkbox.checked
  
  const workspaceId = currentWorkspaceId.value
  const notebookId = currentNotebookId.value
  
  if (!workspaceId || !notebookId) {
    checkbox.checked = !newState
    return
  }
  
  try {
    await integrationStore.toggleIntegrationEnabled(
      integrationId,
      workspaceId,
      notebookId,
      newState
    )
  } catch (err) {
    console.error('Integration toggle error:', err)
    checkbox.checked = !newState
  }
}

async function testConfiguration() {
  if (!expandedIntegrationId.value) return
  
  isTesting.value = true
  testResultMsg.value = null
  
  try {
    const result = await testIntegrationConnection(expandedIntegrationId.value, configData.value)
    testResultMsg.value = result
  } catch (err: any) {
    testResultMsg.value = {
      success: false,
      message: err.message || 'Connection test failed',
    }
  } finally {
    isTesting.value = false
  }
}

async function saveConfiguration() {
  if (!expandedIntegrationId.value || !currentWorkspaceId.value || !currentNotebookId.value) {
    testResultMsg.value = {
      success: false,
      message: 'No workspace or notebook selected',
    }
    return
  }
  
  isSaving.value = true
  testResultMsg.value = null
  
  try {
    await updateIntegrationConfig(
      expandedIntegrationId.value,
      currentWorkspaceId.value,
      currentNotebookId.value,
      configData.value
    )
    testResultMsg.value = {
      success: true,
      message: 'Configuration saved successfully!',
    }
  } catch (err: any) {
    testResultMsg.value = {
      success: false,
      message: err.message || 'Failed to save configuration',
    }
  } finally {
    isSaving.value = false
  }
}

onMounted(async () => {
  if (!integrationStore.integrationsLoaded) {
    const workspaceId = currentWorkspaceId.value
    const notebookId = currentNotebookId.value
    
    if (workspaceId && notebookId) {
      await integrationStore.loadIntegrations(workspaceId, notebookId)
    }
  }
})
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

.loading-state,
.empty-state {
  padding: 3rem;
  text-align: center;
  color: var(--color-text-tertiary);
  font-style: italic;
}

.integrations-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.integration-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-medium);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.integration-card-expanded {
  border-color: var(--notebook-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.5rem;
  cursor: pointer;
  transition: background 0.2s;
}

.card-header:hover {
  background: var(--color-bg-tertiary);
}

.header-main {
  flex: 1;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.integration-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.integration-version {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border-radius: 10px;
}

.integration-description {
  margin: 0 0 0.75rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
  font-size: 0.9375rem;
}

.integration-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.meta-chip {
  font-size: 0.75rem;
  padding: 0.1875rem 0.5rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: 4px;
  color: var(--color-text-tertiary);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-left: 1rem;
}

.toggle-switch-label {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
  cursor: pointer;
}

.toggle-checkbox {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background-color: #ccc;
  border-radius: 26px;
  transition: 0.25s;
}

.toggle-slider::before {
  content: "";
  position: absolute;
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: 0.25s;
}

.toggle-checkbox:checked + .toggle-slider {
  background-color: var(--notebook-accent);
}

.toggle-checkbox:checked + .toggle-slider::before {
  transform: translateX(24px);
}

.expand-btn {
  background: none;
  border: 1px solid var(--color-border-medium);
  padding: 0.5rem;
  width: 36px;
  height: 36px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
}

.expand-btn:hover {
  background: var(--color-bg-primary);
  border-color: var(--notebook-accent);
  color: var(--notebook-accent);
}

.card-config {
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-primary);
  padding: 1.5rem;
}

.config-loading,
.config-error {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-tertiary);
}

.config-error {
  color: var(--color-error);
}

.retry-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: var(--notebook-accent);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.warning-box {
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  color: #856404;
  font-size: 0.9375rem;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-section-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.no-config {
  padding: 1rem;
  text-align: center;
  color: var(--color-text-tertiary);
  font-style: italic;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-label {
  font-weight: 500;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
}

.required-mark {
  color: #dc3545;
  margin-left: 0.25rem;
}

.field-input {
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  font-size: 0.9375rem;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 0.2s;
}

.field-input:focus {
  outline: none;
  border-color: var(--notebook-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--notebook-accent) 15%, transparent);
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
}

.field-checkbox {
  width: auto;
  cursor: pointer;
}

.field-help {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
  line-height: 1.4;
}

.form-actions {
  display: flex;
  gap: 1rem;
  padding-top: 0.5rem;
}

.btn-test,
.btn-save {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 4px;
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-test {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-medium);
}

.btn-test:hover:not(:disabled) {
  background: var(--color-bg-hover);
}

.btn-save {
  background: var(--notebook-accent);
  color: white;
}

.btn-save:hover:not(:disabled) {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.btn-test:disabled,
.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-box {
  padding: 1rem;
  border-radius: 4px;
  font-size: 0.9375rem;
}

.result-success {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.result-error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.result-box p {
  margin: 0 0 0.5rem;
}

.result-details {
  margin: 0.5rem 0 0;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  font-size: 0.8125rem;
  overflow-x: auto;
  white-space: pre-wrap;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-section-title {
  margin: 0;
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.blocks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.block-card {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
}

.block-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.block-content {
  flex: 1;
}

.block-name {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
}

.block-desc {
  margin: 0.25rem 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.block-syntax {
  display: block;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  font-size: 0.8125rem;
  color: var(--color-text-primary);
}

.endpoints-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.endpoint-card {
  padding: 1rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
}

.endpoint-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.endpoint-method {
  background: var(--notebook-accent);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.endpoint-path {
  background: var(--color-bg-primary);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--color-border-medium);
  font-size: 0.8125rem;
  color: var(--color-text-primary);
}

.endpoint-desc {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}
</style>
