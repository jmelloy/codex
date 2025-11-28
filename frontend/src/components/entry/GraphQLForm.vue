<script setup lang="ts">
import { ref, computed, defineEmits, defineProps } from 'vue'

const props = defineProps<{
  modelValue?: {
    url?: string
    query?: string
    variables?: Record<string, unknown>
    headers?: Record<string, string>
    operation_name?: string
  }
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, unknown>): void
}>()

const url = ref(props.modelValue?.url || '')
const query = ref(props.modelValue?.query || '')
const variablesJson = ref(
  props.modelValue?.variables
    ? JSON.stringify(props.modelValue.variables, null, 2)
    : ''
)
const headersJson = ref(
  props.modelValue?.headers
    ? JSON.stringify(props.modelValue.headers, null, 2)
    : ''
)
const operationName = ref(props.modelValue?.operation_name || '')

const variablesError = ref('')
const headersError = ref('')

const inputs = computed(() => {
  const result: Record<string, unknown> = {
    url: url.value,
    query: query.value,
  }

  if (operationName.value.trim()) {
    result.operation_name = operationName.value
  }

  if (variablesJson.value.trim()) {
    try {
      result.variables = JSON.parse(variablesJson.value)
      variablesError.value = ''
    } catch {
      variablesError.value = 'Invalid JSON'
    }
  }

  if (headersJson.value.trim()) {
    try {
      result.headers = JSON.parse(headersJson.value)
      headersError.value = ''
    } catch {
      headersError.value = 'Invalid JSON'
    }
  }

  return result
})

const updateValue = () => {
  emit('update:modelValue', inputs.value)
}

// Example GraphQL query templates
const queryTemplates = [
  {
    label: 'Simple Query',
    query: `query {
  users {
    id
    name
    email
  }
}`,
    variables: '',
  },
  {
    label: 'Query with Variables',
    query: `query GetUser($id: ID!) {
  user(id: $id) {
    id
    name
    email
  }
}`,
    variables: '{\n  "id": "1"\n}',
  },
  {
    label: 'Mutation',
    query: `mutation CreateUser($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    name
    email
  }
}`,
    variables: '{\n  "input": {\n    "name": "John Doe",\n    "email": "john@example.com"\n  }\n}',
  },
]

const applyTemplate = (template: typeof queryTemplates[0]) => {
  query.value = template.query
  variablesJson.value = template.variables
  updateValue()
}
</script>

<template>
  <div class="graphql-form">
    <div class="form-group">
      <label for="url">GraphQL Endpoint URL</label>
      <input
        id="url"
        v-model="url"
        type="url"
        placeholder="https://api.example.com/graphql"
        @input="updateValue"
      />
    </div>

    <div class="form-group">
      <label for="query">GraphQL Query</label>
      <div class="query-templates">
        <span class="template-label">Templates:</span>
        <button
          v-for="template in queryTemplates"
          :key="template.label"
          type="button"
          class="template-btn"
          @click="applyTemplate(template)"
        >
          {{ template.label }}
        </button>
      </div>
      <textarea
        id="query"
        v-model="query"
        rows="10"
        placeholder="query { users { id name } }"
        @input="updateValue"
      ></textarea>
      <span class="hint">GraphQL query or mutation</span>
    </div>

    <div class="form-group">
      <label for="variables">Variables (JSON)</label>
      <textarea
        id="variables"
        v-model="variablesJson"
        rows="4"
        placeholder='{"id": "123"}'
        @input="updateValue"
        :class="{ error: variablesError }"
      ></textarea>
      <span v-if="variablesError" class="error-text">{{ variablesError }}</span>
      <span v-else class="hint">Optional: JSON object with query variables</span>
    </div>

    <div class="form-group">
      <label for="operation-name">Operation Name</label>
      <input
        id="operation-name"
        v-model="operationName"
        type="text"
        placeholder="GetUser"
        @input="updateValue"
      />
      <span class="hint">Optional: Operation name for documents with multiple operations</span>
    </div>

    <div class="form-group">
      <label for="headers">HTTP Headers (JSON)</label>
      <textarea
        id="headers"
        v-model="headersJson"
        rows="3"
        placeholder='{"Authorization": "Bearer token"}'
        @input="updateValue"
        :class="{ error: headersError }"
      ></textarea>
      <span v-if="headersError" class="error-text">{{ headersError }}</span>
      <span v-else class="hint">Optional: Additional HTTP headers</span>
    </div>
  </div>
</template>

<style scoped>
.graphql-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
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
.form-group textarea {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-family: inherit;
}

.form-group textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus {
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

.query-templates {
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
</style>
