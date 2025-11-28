<script setup lang="ts">
import { ref, computed, defineEmits, defineProps } from 'vue'

const props = defineProps<{
  modelValue?: {
    connection_string?: string
    query?: string
    parameters?: Record<string, unknown>
    max_rows?: number
  }
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, unknown>): void
}>()

const connectionString = ref(props.modelValue?.connection_string || '')
const query = ref(props.modelValue?.query || '')
const parametersJson = ref(
  props.modelValue?.parameters
    ? JSON.stringify(props.modelValue.parameters, null, 2)
    : ''
)
const maxRows = ref(props.modelValue?.max_rows || 1000)

const parametersError = ref('')

const inputs = computed(() => {
  const result: Record<string, unknown> = {
    connection_string: connectionString.value,
    query: query.value,
    max_rows: maxRows.value,
  }

  if (parametersJson.value.trim()) {
    try {
      result.parameters = JSON.parse(parametersJson.value)
      parametersError.value = ''
    } catch {
      parametersError.value = 'Invalid JSON'
    }
  }

  return result
})

const updateValue = () => {
  emit('update:modelValue', inputs.value)
}

// Predefined connection string templates
const connectionTemplates = [
  { label: 'SQLite (memory)', value: 'sqlite:///:memory:' },
  { label: 'SQLite (file)', value: 'sqlite:///path/to/database.db' },
  { label: 'PostgreSQL', value: 'postgresql://user:password@localhost:5432/dbname' },
  { label: 'MySQL', value: 'mysql://user:password@localhost:3306/dbname' },
]

const applyTemplate = (template: string) => {
  connectionString.value = template
  updateValue()
}
</script>

<template>
  <div class="database-query-form">
    <div class="form-group">
      <label for="connection-string">Connection String</label>
      <div class="input-with-helper">
        <input
          id="connection-string"
          v-model="connectionString"
          type="text"
          placeholder="sqlite:///path/to/db.sqlite"
          @input="updateValue"
        />
        <div class="template-buttons">
          <button
            v-for="template in connectionTemplates"
            :key="template.label"
            type="button"
            class="template-btn"
            @click="applyTemplate(template.value)"
          >
            {{ template.label }}
          </button>
        </div>
      </div>
      <span class="hint">SQLAlchemy connection string format</span>
    </div>

    <div class="form-group">
      <label for="query">SQL Query</label>
      <textarea
        id="query"
        v-model="query"
        rows="6"
        placeholder="SELECT * FROM users WHERE id = :user_id"
        @input="updateValue"
      ></textarea>
      <span class="hint">Use :param_name for named parameters</span>
    </div>

    <div class="form-group">
      <label for="parameters">Parameters (JSON)</label>
      <textarea
        id="parameters"
        v-model="parametersJson"
        rows="4"
        placeholder='{"user_id": 123}'
        @input="updateValue"
        :class="{ error: parametersError }"
      ></textarea>
      <span v-if="parametersError" class="error-text">{{ parametersError }}</span>
      <span v-else class="hint">Optional: JSON object with query parameters</span>
    </div>

    <div class="form-group">
      <label for="max-rows">Max Rows</label>
      <input
        id="max-rows"
        v-model.number="maxRows"
        type="number"
        min="1"
        max="10000"
        @input="updateValue"
      />
      <span class="hint">Maximum number of rows to return (default: 1000)</span>
    </div>
  </div>
</template>

<style scoped>
.database-query-form {
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

.input-with-helper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.template-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
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
