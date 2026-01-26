<template>
  <div class="base-input-wrapper">
    <label
      v-if="label"
      :for="id"
      class="block mb-2 font-medium"
      style="color: var(--notebook-text)"
    >
      {{ label }}
    </label>
    <input
      :id="id"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      :minlength="minlength"
      :maxlength="maxlength"
      @input="handleInput"
      class="auth-input w-full px-3 py-2 rounded text-base focus:outline-none"
      :class="{ 'disabled:cursor-not-allowed disabled:opacity-60': disabled }"
    />
    <p v-if="error" class="mt-1 text-sm" style="color: var(--pen-red)">
      {{ error }}
    </p>
  </div>
</template>

<script setup lang="ts">
interface Props {
  id?: string
  type?: 'text' | 'email' | 'password' | 'number'
  modelValue?: string | number
  label?: string
  placeholder?: string
  required?: boolean
  disabled?: boolean
  minlength?: number
  maxlength?: number
  error?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  required: false,
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.auth-input {
  border: 1px solid var(--page-border);
  background: var(--notebook-bg);
  color: var(--notebook-text);
}

.auth-input:focus {
  border-color: var(--notebook-accent);
}

.auth-input::placeholder {
  color: color-mix(in srgb, var(--notebook-text) 40%, transparent);
}

.auth-input:disabled {
  opacity: 0.6;
  background: color-mix(in srgb, var(--notebook-text) 5%, transparent);
}
</style>
