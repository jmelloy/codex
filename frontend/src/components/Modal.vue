<template>
  <div v-if="modelValue" class="modal" @click.self="handleClose">
    <div class="modal-content">
      <h3 v-if="title">{{ title }}</h3>
      <slot></slot>
      <div class="modal-actions" v-if="!hideActions">
        <button type="button" @click="handleCancel">{{ cancelText }}</button>
        <button type="button" @click="handleConfirm" class="btn-primary">{{ confirmText }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  modelValue: boolean
  title?: string
  confirmText?: string
  cancelText?: string
  hideActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  hideActions: false
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': []
  'cancel': []
}>()

function handleClose() {
  emit('update:modelValue', false)
  emit('cancel')
}

function handleCancel() {
  emit('update:modelValue', false)
  emit('cancel')
}

function handleConfirm() {
  emit('confirm')
}
</script>

<style scoped>
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  width: 100%;
  max-width: 400px;
}

.modal-content h3 {
  margin: 0 0 1rem;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.modal-actions button[type='button'] {
  background: #e2e8f0;
}

.modal-actions .btn-primary {
  background: #667eea;
  color: white;
}
</style>
