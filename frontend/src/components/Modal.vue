<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-backdrop" @click.self="handleClose">
      <div class="modal-content">
        <h3 v-if="title" class="m-0 mb-4 text-lg font-semibold text-text-primary">
          {{ title }}
        </h3>
        <slot></slot>
        <div class="modal-actions flex gap-2 justify-end mt-6" v-if="!hideActions">
          <button
            type="button"
            @click="handleCancel"
            class="px-4 py-2 bg-bg-disabled text-text-primary border-none rounded cursor-pointer hover:bg-border-medium transition font-medium"
          >
            {{ cancelText }}
          </button>
          <button
            type="button"
            @click="handleConfirm"
            class="btn-primary px-4 py-2 bg-primary text-text-inverse border-none rounded cursor-pointer hover:bg-primary-hover transition font-medium"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
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
  confirmText: "Confirm",
  cancelText: "Cancel",
  hideActions: false,
})

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  confirm: []
  cancel: []
}>()

function handleClose() {
  emit("update:modelValue", false)
  emit("cancel")
}

function handleCancel() {
  emit("update:modelValue", false)
  emit("cancel")
}

function handleConfirm() {
  emit("confirm")
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* Dark theme uses a lighter overlay for better contrast */
:global(.theme-blueprint) .modal-backdrop {
  background-color: rgba(0, 0, 0, 0.7);
}

.modal-content {
  background-color: var(--color-bg-primary);
  padding: 2rem;
  border-radius: 0.5rem;
  width: 100%;
  max-width: 28rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--color-border-light);
  /* Ensure solid background - prevent any transparency inheritance */
  opacity: 1;
  isolation: isolate;
}

/* Dark theme modal styling */
:global(.theme-blueprint) .modal-content {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
}
</style>
