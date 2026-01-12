<template>
  <div class="form-group">
    <label v-if="label" :for="id">{{ label }}</label>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
interface Props {
  label?: string
  id?: string
}

defineProps<Props>()
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
