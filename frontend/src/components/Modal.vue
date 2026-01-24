<template>
  <div v-if="modelValue" class="modal fixed inset-0 bg-black/50 flex items-center justify-center z-[1000]" @click.self="handleClose">
    <div class="modal-content bg-bg-primary p-8 rounded-lg w-full max-w-md shadow-xl border border-border-light">
      <h3 v-if="title" class="m-0 mb-4 text-lg font-semibold text-text-primary">{{ title }}</h3>
      <slot></slot>
      <div class="modal-actions flex gap-2 justify-end mt-6" v-if="!hideActions">
        <button type="button" @click="handleCancel" class="px-4 py-2 bg-bg-disabled text-text-primary border-none rounded cursor-pointer hover:bg-border-medium transition font-medium">{{ cancelText }}</button>
        <button type="button" @click="handleConfirm" class="btn-primary px-4 py-2 bg-primary text-text-inverse border-none rounded cursor-pointer hover:bg-primary-hover transition font-medium">{{ confirmText }}</button>
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
/* Tailwind classes used, minimal custom styles needed */
</style>
