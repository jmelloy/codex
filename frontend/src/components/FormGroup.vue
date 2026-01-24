<template>
  <div class="mb-4">
    <label v-if="label" :for="id" class="block mb-2 font-medium">{{ label }}</label>
    <slot :inputId="id"></slot>
  </div>
</template>

<script setup lang="ts">
interface Props {
  label?: string
  id?: string
}

const props = defineProps<Props>()

// Generate a unique ID once at setup time if not provided
// Using random number to ensure uniqueness across component instances
const id = props.id || `input-${Math.random().toString(36).substring(2, 11)}`
</script>

<style>
/* Global styles for form inputs used in FormGroup slots */
.mb-4 input,
.mb-4 textarea,
.mb-4 select {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  box-sizing: border-box;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.mb-4 input:focus,
.mb-4 textarea:focus,
.mb-4 select:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.mb-4 input::placeholder,
.mb-4 textarea::placeholder {
  color: var(--color-text-placeholder);
}

.mb-4 label {
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}
</style>
