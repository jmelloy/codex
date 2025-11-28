<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import DatabaseQueryForm from '@/components/entry/DatabaseQueryForm.vue'
import GraphQLForm from '@/components/entry/GraphQLForm.vue'
import ApiCallForm from '@/components/entry/ApiCallForm.vue'
import CustomForm from '@/components/entry/CustomForm.vue'

// Entry form data
const entryType = ref('custom')
const title = ref('')
const inputs = ref<Record<string, unknown>>({})
const tags = ref('')

const entryTypes = [
  { value: 'custom', label: 'Custom Entry', description: 'Manual entry for notes and observations', icon: '📝' },
  { value: 'api_call', label: 'API Call', description: 'HTTP API request tracking', icon: '🌐' },
  { value: 'database_query', label: 'SQL Query', description: 'Execute SQL queries against databases', icon: '🗃️' },
  { value: 'graphql', label: 'GraphQL', description: 'GraphQL API queries and mutations', icon: '◈' },
]

const currentEntryType = computed(() => 
  entryTypes.find(t => t.value === entryType.value)
)

const formComponent = computed(() => {
  switch (entryType.value) {
    case 'database_query':
      return DatabaseQueryForm
    case 'graphql':
      return GraphQLForm
    case 'api_call':
      return ApiCallForm
    case 'custom':
    default:
      return CustomForm
  }
})

// Reset inputs when entry type changes
watch(entryType, () => {
  inputs.value = {}
})

const handleInputsUpdate = (newInputs: Record<string, unknown>) => {
  inputs.value = newInputs
}

const isValid = computed(() => {
  if (!title.value.trim()) return false
  
  // Validate based on entry type
  switch (entryType.value) {
    case 'database_query':
      return !!(inputs.value.connection_string && inputs.value.query)
    case 'graphql':
      return !!(inputs.value.url && inputs.value.query)
    case 'api_call':
      return !!(inputs.value.url)
    case 'custom':
    default:
      return true
  }
})

const showPreview = ref(false)

const submitEntry = () => {
  showPreview.value = true
}
</script>

<template>
  <div class="demo-view">
    <header class="page-header">
      <div class="breadcrumb">
        <span>Notebooks</span>
        <span>/</span>
        <span>Demo Notebook</span>
        <span>/</span>
        <span>Demo Page</span>
        <span>/</span>
        <span>New Entry</span>
      </div>

      <h1>Create New Entry (Demo)</h1>
      <p class="subtitle">This is a demonstration of the entry creation forms for SQL, GraphQL, and API plugins.</p>
    </header>

    <form class="entry-form card" @submit.prevent="submitEntry">
      <!-- Entry Type Selection -->
      <section class="form-section">
        <h2>Entry Type</h2>
        <div class="entry-type-grid">
          <button
            v-for="type in entryTypes"
            :key="type.value"
            type="button"
            class="type-card"
            :class="{ selected: entryType === type.value }"
            @click="entryType = type.value"
          >
            <span class="type-icon">{{ type.icon }}</span>
            <span class="type-label">{{ type.label }}</span>
            <span class="type-description">{{ type.description }}</span>
          </button>
        </div>
      </section>

      <!-- Basic Info -->
      <section class="form-section">
        <h2>Basic Information</h2>
        <div class="form-group">
          <label for="title">Title <span class="required">*</span></label>
          <input
            id="title"
            v-model="title"
            type="text"
            placeholder="Enter a descriptive title for this entry"
            required
          />
        </div>

        <div class="form-group">
          <label for="tags">Tags</label>
          <input
            id="tags"
            v-model="tags"
            type="text"
            placeholder="tag1, tag2, tag3"
          />
          <span class="hint">Comma-separated list of tags</span>
        </div>
      </section>

      <!-- Dynamic Form based on Entry Type -->
      <section class="form-section">
        <h2>{{ currentEntryType?.label }} Configuration</h2>
        <component
          :is="formComponent"
          :model-value="inputs"
          @update:model-value="handleInputsUpdate"
        />
      </section>

      <!-- Preview -->
      <section v-if="showPreview" class="form-section preview-section">
        <h2>Preview</h2>
        <pre class="preview-json">{{ JSON.stringify({ entryType, title, inputs, tags }, null, 2) }}</pre>
      </section>

      <!-- Actions -->
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" @click="showPreview = !showPreview">
          {{ showPreview ? 'Hide' : 'Show' }} Preview
        </button>
        <button
          type="submit"
          class="btn btn-primary"
          :disabled="!isValid"
        >
          Create Entry
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.demo-view {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.breadcrumb {
  display: flex;
  gap: 0.5rem;
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.subtitle {
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
}

.entry-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-section h2 {
  font-size: 1.125rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.entry-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.25rem;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.type-card:hover {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.02);
}

.type-card.selected {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.05);
}

.type-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.type-label {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.type-description {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  font-size: 0.875rem;
}

.required {
  color: #dc2626;
}

.form-group input {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.preview-section {
  background: var(--color-bg-secondary);
  padding: 1rem;
  border-radius: var(--radius-md);
}

.preview-json {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: var(--radius-md);
  overflow-x: auto;
  font-size: 0.875rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}
</style>
