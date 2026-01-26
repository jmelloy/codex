<template>
  <button
    :type="type"
    :disabled="disabled"
    :class="buttonClasses"
    @click="$emit('click', $event)"
  >
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  fullWidth?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  type: 'button',
  disabled: false,
  fullWidth: false
})

defineEmits<{
  click: [event: MouseEvent]
}>()

const buttonClasses = computed(() => {
  const classes: string[] = [
    'base-button',
    'border',
    'rounded',
    'cursor-pointer',
    'transition',
    'disabled:opacity-50',
    'disabled:cursor-not-allowed'
  ]

  // Variant styles
  switch (props.variant) {
    case 'primary':
      classes.push('notebook-button')
      break
    case 'secondary':
      classes.push(
        'border-border-medium',
        'bg-bg-primary',
        'text-text-primary',
        'hover:bg-bg-hover'
      )
      break
    case 'danger':
      classes.push(
        'bg-red-600',
        'text-white',
        'border-red-600',
        'hover:bg-red-700'
      )
      break
  }

  // Size styles
  switch (props.size) {
    case 'sm':
      classes.push('px-2', 'py-1', 'text-sm')
      break
    case 'md':
      classes.push('px-3', 'py-2', 'text-base')
      break
    case 'lg':
      classes.push('px-4', 'py-3', 'text-lg')
      break
  }

  // Full width
  if (props.fullWidth) {
    classes.push('w-full')
  }

  return classes.join(' ')
})
</script>

<style scoped>
.base-button {
  border: none;
}
</style>
