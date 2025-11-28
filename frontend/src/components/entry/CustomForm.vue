<script setup lang="ts">
import { ref, computed, defineEmits, defineProps } from 'vue'

const props = defineProps<{
  modelValue?: {
    description?: string
    notes?: string
    outputs?: Record<string, unknown>
  }
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, unknown>): void
}>()

const description = ref(props.modelValue?.description || '')
const notes = ref(props.modelValue?.notes || '')
const outputsJson = ref(
  props.modelValue?.outputs
    ? JSON.stringify(props.modelValue.outputs, null, 2)
    : ''
)

const outputsError = ref('')

const inputs = computed(() => {
  const result: Record<string, unknown> = {
    description: description.value,
    notes: notes.value,
  }

  if (outputsJson.value.trim()) {
    try {
      result.outputs = JSON.parse(outputsJson.value)
      outputsError.value = ''
    } catch {
      outputsError.value = 'Invalid JSON'
    }
  }

  return result
})

const updateValue = () => {
  emit('update:modelValue', inputs.value)
}
</script>

<template>
  <div class="custom-form">
    <div class="form-group">
      <label for="description">Description</label>
      <textarea
        id="description"
        v-model="description"
        rows="4"
        placeholder="Describe this entry..."
        @input="updateValue"
      ></textarea>
      <span class="hint">A brief description of this manual entry</span>
    </div>

    <div class="form-group">
      <label for="notes">Notes</label>
      <textarea
        id="notes"
        v-model="notes"
        rows="6"
        placeholder="Additional notes, observations, or details..."
        @input="updateValue"
      ></textarea>
      <span class="hint">Any additional information or observations</span>
    </div>

    <div class="form-group">
      <label for="outputs">Outputs (JSON)</label>
      <textarea
        id="outputs"
        v-model="outputsJson"
        rows="4"
        placeholder='{"result": "value"}'
        @input="updateValue"
        :class="{ error: outputsError }"
      ></textarea>
      <span v-if="outputsError" class="error-text">{{ outputsError }}</span>
      <span v-else class="hint">Optional: Any output data as JSON</span>
    </div>
  </div>
</template>

<style scoped>
.custom-form {
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

.form-group textarea {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
}

.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

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
</style>
