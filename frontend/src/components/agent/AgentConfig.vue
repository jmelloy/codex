<template>
  <div class="agent-config">
    <h3 class="config-title">{{ isEditing ? "Edit Agent" : "Create Agent" }}</h3>

    <form @submit.prevent="handleSubmit" class="config-form">
      <!-- Basic Info -->
      <div class="form-section">
        <div class="form-field">
          <label for="agent-name" class="field-label">Name <span class="required">*</span></label>
          <input
            id="agent-name"
            v-model="form.name"
            type="text"
            required
            maxlength="100"
            placeholder="Research Assistant"
            class="field-input"
          />
        </div>

        <div class="form-field">
          <label for="agent-description" class="field-label">Description</label>
          <textarea
            id="agent-description"
            v-model="form.description"
            rows="2"
            placeholder="What does this agent do?"
            class="field-input"
          />
        </div>
      </div>

      <!-- Provider & Model -->
      <div class="form-section">
        <h4 class="section-heading">Model Configuration</h4>
        <div class="form-row">
          <div class="form-field">
            <label for="agent-provider" class="field-label">Provider <span class="required">*</span></label>
            <select id="agent-provider" v-model="form.provider" required class="field-input">
              <option value="">Select provider...</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama (Local)</option>
              <option value="azure">Azure OpenAI</option>
              <option value="bedrock">AWS Bedrock</option>
            </select>
          </div>
          <div class="form-field">
            <label for="agent-model" class="field-label">Model <span class="required">*</span></label>
            <input
              id="agent-model"
              v-model="form.model"
              type="text"
              required
              :placeholder="modelPlaceholder"
              class="field-input"
            />
          </div>
        </div>
      </div>

      <!-- Credentials -->
      <div class="form-section">
        <h4 class="section-heading">Credentials</h4>
        <div class="form-field">
          <label for="agent-apikey" class="field-label">API Key</label>
          <input
            id="agent-apikey"
            v-model="apiKey"
            type="password"
            placeholder="Enter API key (stored encrypted)"
            autocomplete="off"
            class="field-input"
          />
          <small class="field-help">Keys are stored encrypted and never returned by the API.</small>
        </div>
        <div v-if="form.provider === 'ollama' || form.provider === 'azure'" class="form-field">
          <label for="agent-apibase" class="field-label">API Base URL</label>
          <input
            id="agent-apibase"
            v-model="apiBase"
            type="text"
            :placeholder="form.provider === 'ollama' ? 'http://localhost:11434' : 'https://your-resource.openai.azure.com'"
            class="field-input"
          />
        </div>
        <!-- Existing credentials -->
        <div v-if="existingCredentials.length > 0" class="credentials-list">
          <div v-for="cred in existingCredentials" :key="cred.key_name" class="credential-item">
            <span class="credential-name">{{ cred.key_name }}</span>
            <span class="credential-date">Set {{ formatDate(cred.created_at) }}</span>
            <button type="button" @click="handleDeleteCredential(cred.key_name)" class="credential-delete">
              Remove
            </button>
          </div>
        </div>
      </div>

      <!-- System Prompt -->
      <div class="form-section">
        <h4 class="section-heading">System Prompt</h4>
        <div class="form-field">
          <textarea
            v-model="form.system_prompt"
            rows="4"
            placeholder="Custom system prompt (optional). If blank, a default prompt will be generated from the agent's scope."
            class="field-input field-mono"
          />
        </div>
      </div>

      <!-- Rate Limits -->
      <div class="form-section">
        <h4 class="section-heading">Rate Limits</h4>
        <div class="form-row">
          <div class="form-field">
            <label for="agent-rph" class="field-label">Requests / Hour</label>
            <input
              id="agent-rph"
              v-model.number="form.max_requests_per_hour"
              type="number"
              min="1"
              class="field-input"
            />
          </div>
          <div class="form-field">
            <label for="agent-tpr" class="field-label">Max Tokens / Request</label>
            <input
              id="agent-tpr"
              v-model.number="form.max_tokens_per_request"
              type="number"
              min="1"
              class="field-input"
            />
          </div>
        </div>
      </div>

      <!-- Scope Editor -->
      <div class="form-section">
        <AgentScopeEditor
          :scope="scopeForEditor"
          :can-read="form.can_read"
          :can-write="form.can_write"
          :can-create="form.can_create"
          :can-delete="form.can_delete"
          @update="handleScopeUpdate"
        />
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button type="button" @click="$emit('cancel')" class="btn-secondary">Cancel</button>
        <button type="submit" :disabled="saving" class="btn-primary">
          {{ saving ? "Saving..." : isEditing ? "Update Agent" : "Create Agent" }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue"
import { useAgentStore } from "../../stores/agent"
import AgentScopeEditor from "./AgentScopeEditor.vue"
import type { Agent, AgentScope, Credential } from "../../services/agent"

const props = defineProps<{
  workspaceId: number
  agent?: Agent
}>()

const emit = defineEmits<{
  cancel: []
  saved: [agent: Agent]
}>()

const agentStore = useAgentStore()
const saving = ref(false)
const apiKey = ref("")
const apiBase = ref("")
const existingCredentials = ref<Credential[]>([])

const isEditing = computed(() => !!props.agent)

const form = reactive({
  name: props.agent?.name || "",
  description: props.agent?.description || "",
  provider: props.agent?.provider || "",
  model: props.agent?.model || "",
  can_read: props.agent?.can_read ?? true,
  can_write: props.agent?.can_write ?? false,
  can_create: props.agent?.can_create ?? false,
  can_delete: props.agent?.can_delete ?? false,
  max_requests_per_hour: props.agent?.max_requests_per_hour ?? 100,
  max_tokens_per_request: props.agent?.max_tokens_per_request ?? 4000,
  system_prompt: props.agent?.system_prompt || "",
  scope: { ...(props.agent?.scope || { notebooks: ["*"], folders: ["*"], file_types: ["*"] }) },
})

const scopeForEditor = computed<AgentScope>(() => ({
  notebooks: form.scope.notebooks || ["*"],
  folders: form.scope.folders || ["*"],
  file_types: form.scope.file_types || ["*"],
}))

const modelPlaceholder = computed(() => {
  switch (form.provider) {
    case "openai":
      return "gpt-4o"
    case "anthropic":
      return "claude-sonnet-4-20250514"
    case "ollama":
      return "llama3"
    case "azure":
      return "azure/gpt-4"
    case "bedrock":
      return "bedrock/anthropic.claude-3"
    default:
      return "model-name"
  }
})

function handleScopeUpdate(update: {
  scope: AgentScope
  can_read: boolean
  can_write: boolean
  can_create: boolean
  can_delete: boolean
}) {
  form.scope = update.scope
  form.can_read = update.can_read
  form.can_write = update.can_write
  form.can_create = update.can_create
  form.can_delete = update.can_delete
}

async function handleSubmit() {
  saving.value = true
  try {
    let agent: Agent
    const data = {
      name: form.name,
      description: form.description || undefined,
      provider: form.provider,
      model: form.model,
      scope: form.scope,
      can_read: form.can_read,
      can_write: form.can_write,
      can_create: form.can_create,
      can_delete: form.can_delete,
      max_requests_per_hour: form.max_requests_per_hour,
      max_tokens_per_request: form.max_tokens_per_request,
      system_prompt: form.system_prompt || undefined,
    }

    if (isEditing.value && props.agent) {
      agent = await agentStore.updateAgent(props.agent.id, data)
    } else {
      agent = await agentStore.createAgent(props.workspaceId, data)
    }

    // Save credentials if provided
    if (apiKey.value) {
      await agentStore.setCredential(agent.id, "api_key", apiKey.value)
      apiKey.value = ""
    }
    if (apiBase.value) {
      await agentStore.setCredential(agent.id, "api_base", apiBase.value)
      apiBase.value = ""
    }

    emit("saved", agent)
  } catch {
    // Error handled in store
  } finally {
    saving.value = false
  }
}

async function handleDeleteCredential(keyName: string) {
  if (!props.agent) return
  try {
    await agentStore.deleteCredential(props.agent.id, keyName)
    existingCredentials.value = existingCredentials.value.filter(
      (c) => c.key_name !== keyName
    )
  } catch {
    // Error handled in store
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString()
}

onMounted(async () => {
  if (props.agent) {
    await agentStore.fetchCredentials(props.agent.id)
    existingCredentials.value = [...agentStore.credentials]
  }
})
</script>

<style scoped>
.agent-config {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-heading {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-primary);
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--color-border-light);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.required {
  color: #dc3545;
}

.field-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border-medium);
  border-radius: 4px;
  font-size: 0.875rem;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 0.2s;
}

.field-input:focus {
  outline: none;
  border-color: var(--notebook-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--notebook-accent) 15%, transparent);
}

.field-mono {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}

.field-help {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.credentials-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.credential-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-light);
  border-radius: 4px;
  font-size: 0.8125rem;
}

.credential-name {
  font-weight: 500;
  font-family: var(--font-mono);
  color: var(--color-text-primary);
}

.credential-date {
  flex: 1;
  color: var(--color-text-tertiary);
}

.credential-delete {
  background: none;
  border: none;
  color: #dc3545;
  cursor: pointer;
  font-size: 0.8125rem;
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  transition: background 0.2s;
}

.credential-delete:hover {
  background: rgba(220, 53, 69, 0.1);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border-light);
}

.btn-primary,
.btn-secondary {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--notebook-accent);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: color-mix(in srgb, var(--notebook-accent) 85%, black);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-medium);
}

.btn-secondary:hover {
  background: var(--color-bg-hover, var(--color-bg-tertiary));
}
</style>
