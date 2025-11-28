<script setup lang="ts">
import { ref, computed, defineEmits, defineProps } from 'vue'

const props = defineProps<{
  modelValue?: {
    url?: string
    method?: string
    headers?: Record<string, string>
    body?: unknown
  }
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, unknown>): void
}>()

const url = ref(props.modelValue?.url || '')
const method = ref(props.modelValue?.method || 'GET')
const headersJson = ref(
  props.modelValue?.headers
    ? JSON.stringify(props.modelValue.headers, null, 2)
    : ''
)
const bodyJson = ref(
  props.modelValue?.body
    ? JSON.stringify(props.modelValue.body, null, 2)
    : ''
)

const headersError = ref('')
const bodyError = ref('')

const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

const inputs = computed(() => {
  const result: Record<string, unknown> = {
    url: url.value,
    method: method.value,
  }

  if (headersJson.value.trim()) {
    try {
      result.headers = JSON.parse(headersJson.value)
      headersError.value = ''
    } catch {
      headersError.value = 'Invalid JSON'
    }
  }

  if (bodyJson.value.trim() && ['POST', 'PUT', 'PATCH'].includes(method.value)) {
    try {
      result.body = JSON.parse(bodyJson.value)
      bodyError.value = ''
    } catch {
      bodyError.value = 'Invalid JSON'
    }
  }

  return result
})

const updateValue = () => {
  emit('update:modelValue', inputs.value)
}

const showBody = computed(() => ['POST', 'PUT', 'PATCH'].includes(method.value))

// Common header templates
const headerTemplates = [
  { label: 'JSON Content-Type', value: '{\n  "Content-Type": "application/json"\n}' },
  { label: 'Bearer Auth', value: '{\n  "Authorization": "Bearer YOUR_TOKEN"\n}' },
  { label: 'API Key', value: '{\n  "X-API-Key": "YOUR_API_KEY"\n}' },
]

const applyHeaderTemplate = (template: string) => {
  if (headersJson.value.trim()) {
    try {
      const existing = JSON.parse(headersJson.value)
      const newHeaders = JSON.parse(template)
      headersJson.value = JSON.stringify({ ...existing, ...newHeaders }, null, 2)
    } catch {
      headersJson.value = template
    }
  } else {
    headersJson.value = template
  }
  updateValue()
}
</script>

<template>
  <div class="api-call-form">
    <div class="form-row">
      <div class="form-group method-group">
        <label for="method">Method</label>
        <select id="method" v-model="method" @change="updateValue">
          <option v-for="m in httpMethods" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>

      <div class="form-group url-group">
        <label for="url">URL</label>
        <input
          id="url"
          v-model="url"
          type="url"
          placeholder="https://api.example.com/endpoint"
          @input="updateValue"
        />
      </div>
    </div>

    <div class="form-group">
      <label for="headers">HTTP Headers (JSON)</label>
      <div class="header-templates">
        <span class="template-label">Add:</span>
        <button
          v-for="template in headerTemplates"
          :key="template.label"
          type="button"
          class="template-btn"
          @click="applyHeaderTemplate(template.value)"
        >
          {{ template.label }}
        </button>
      </div>
      <textarea
        id="headers"
        v-model="headersJson"
        rows="4"
        placeholder='{"Content-Type": "application/json", "Authorization": "Bearer token"}'
        @input="updateValue"
        :class="{ error: headersError }"
      ></textarea>
      <span v-if="headersError" class="error-text">{{ headersError }}</span>
      <span v-else class="hint">Optional: HTTP headers as JSON object</span>
    </div>

    <div v-if="showBody" class="form-group">
      <label for="body">Request Body (JSON)</label>
      <textarea
        id="body"
        v-model="bodyJson"
        rows="8"
        placeholder='{"key": "value"}'
        @input="updateValue"
        :class="{ error: bodyError }"
      ></textarea>
      <span v-if="bodyError" class="error-text">{{ bodyError }}</span>
      <span v-else class="hint">JSON request body</span>
    </div>

    <div v-else class="info-box">
      <span class="info-icon">ℹ️</span>
      <span>{{ method }} requests typically don't include a body</span>
    </div>
  </div>
</template>

<style scoped>
.api-call-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.method-group {
  flex-shrink: 0;
  width: 120px;
}

.url-group {
  flex: 1;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text);
}

.form-group input,
.form-group textarea,
.form-group select {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-family: inherit;
  background: white;
}

.form-group textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-group input.error,
.form-group textarea.error {
  border-color: #dc2626;
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.error-text {
  font-size: 0.75rem;
  color: #dc2626;
}

.header-templates {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}

.template-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.template-btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-secondary);
}

.template-btn:hover {
  background: var(--color-border);
  color: var(--color-text);
}

.info-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.info-icon {
  font-size: 1rem;
}
</style>
