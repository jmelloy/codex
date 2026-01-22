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
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.mb-4 input:focus,
.mb-4 textarea:focus,
.mb-4 select:focus {
  outline: none;
  border-color: #667eea;
}
</style>
