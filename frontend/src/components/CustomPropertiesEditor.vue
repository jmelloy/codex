<template>
  <div class="property-section">
    <h4>Custom Properties</h4>

    <!-- Existing custom properties -->
    <div class="custom-property-row" v-for="(value, key) in metadata" :key="key">
      <template v-if="editingProperty === key">
        <input
          v-model="editPropertyValueModel"
          @blur="emit('saveEdit', key as string)"
          @keyup.enter="emit('saveEdit', key as string)"
          @keyup.escape="emit('cancelEdit')"
          class="property-edit-input"
        />
        <div class="property-actions-inline">
          <button @click="emit('saveEdit', key as string)" class="btn-action btn-save" title="Save">
            ✓
          </button>
          <button @click="emit('cancelEdit')" class="btn-action btn-cancel" title="Cancel">
            ✕
          </button>
        </div>
      </template>
      <template v-else>
        <span class="property-label">{{ key }}</span>
        <span
          class="property-value editable"
          @click="emit('startEdit', key as string, value)"
          title="Click to edit"
          >{{ formatMetadataValue(value) }}</span
        >
        <button
          @click="emit('removeProperty', key as string)"
          class="btn-remove-property"
          title="Remove property"
        >
          ×
        </button>
      </template>
    </div>

    <!-- Add new property -->
    <div class="add-property-form">
      <input
        v-model="newKeyModel"
        class="property-key-input"
        placeholder="Property name"
        @keyup.enter="emit('focusValue')"
      />
      <input
        v-model="newValueModel"
        class="property-value-input"
        placeholder="Value"
        ref="valueInput"
        @keyup.enter="emit('addProperty')"
      />
      <button
        @click="emit('addProperty')"
        class="btn-add-property"
        :disabled="!newKeyModel.trim()"
        title="Add property"
      >
        +
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"

defineProps<{
  metadata: Record<string, unknown>
  editingProperty: string | null
}>()

const editPropertyValueModel = defineModel<string>("editPropertyValue", { default: "" })
const newKeyModel = defineModel<string>("newPropertyKey", { default: "" })
const newValueModel = defineModel<string>("newPropertyValue", { default: "" })

const emit = defineEmits<{
  startEdit: [key: string, value: unknown]
  saveEdit: [key: string]
  cancelEdit: []
  removeProperty: [key: string]
  addProperty: []
  focusValue: []
}>()

const valueInput = ref<HTMLInputElement | null>(null)

function formatMetadataValue(value: unknown): string {
  if (value === null || value === undefined) return ""
  if (Array.isArray(value)) return value.join(", ")
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

defineExpose({ valueInput })
</script>

<style scoped>
.property-section {
  margin-bottom: var(--spacing-xl);
}

.property-section h4 {
  margin: 0 0 var(--spacing-md);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.custom-property-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-bg-secondary);
}

.custom-property-row .property-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  min-width: 80px;
  flex-shrink: 0;
}

.custom-property-row .property-value {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  word-break: break-all;
  text-align: left;
}

.custom-property-row .property-value.editable {
  cursor: pointer;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  transition: background 0.2s;
}

.custom-property-row .property-value.editable:hover {
  background: var(--color-bg-secondary);
}

.property-edit-input {
  flex: 1;
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border-focus);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
}

.property-edit-input:focus {
  outline: none;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.property-actions-inline {
  display: flex;
  gap: var(--spacing-xs);
}

.btn-action {
  background: none;
  border: none;
  padding: var(--spacing-xs);
  cursor: pointer;
  font-size: var(--text-sm);
  line-height: 1;
  border-radius: var(--radius-sm);
  transition:
    background 0.2s,
    color 0.2s;
}

.btn-save {
  color: var(--color-success, #22c55e);
}

.btn-save:hover {
  background: color-mix(in srgb, var(--color-success, #22c55e) 10%, transparent);
}

.btn-cancel {
  color: var(--color-text-tertiary);
}

.btn-cancel:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.btn-remove-property {
  background: none;
  border: none;
  color: var(--color-text-placeholder);
  cursor: pointer;
  padding: var(--spacing-xs);
  line-height: 1;
  font-size: var(--text-sm);
  transition: color 0.2s;
  opacity: 0;
  flex-shrink: 0;
}

.custom-property-row:hover .btn-remove-property {
  opacity: 1;
}

.btn-remove-property:hover {
  color: var(--color-error);
}

.add-property-form {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-bg-secondary);
}

.property-key-input,
.property-value-input {
  flex: 1;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 0.2s;
}

.property-key-input {
  max-width: 40%;
}

.property-key-input:focus,
.property-value-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
}

.btn-add-property {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-lg);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background 0.2s;
  line-height: 1;
}

.btn-add-property:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-add-property:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-disabled);
  cursor: not-allowed;
}
</style>
