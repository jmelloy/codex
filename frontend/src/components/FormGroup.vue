<template>
  <div class="form-group">
    <label v-if="label" :for="id">{{ label }}</label>
    <slot :inputId="id"></slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  label?: string
  id?: string
}

const props = defineProps<Props>()

// Generate a unique ID if not provided
const id = computed(() => props.id || `input-${Math.random().toString(36).substring(2, 11)}`)
</script>

<style scoped>
.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #667eea;
}
</style>
