<script setup lang="ts">
import { ref, computed, defineEmits, defineProps, watch } from "vue";

const props = defineProps<{
  modelValue?: {
    content?: string;
  };
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: Record<string, unknown>): void;
}>();

const content = ref(props.modelValue?.content || "");

watch(() => props.modelValue, (newVal) => {
  if (newVal?.content !== undefined) {
    content.value = newVal.content;
  }
}, { deep: true });

const inputs = computed(() => ({
  content: content.value,
}));

const updateValue = () => {
  emit("update:modelValue", inputs.value);
};
</script>

<template>
  <div class="text-form">
    <div class="form-group">
      <label for="content">Content</label>
      <textarea
        id="content"
        v-model="content"
        rows="10"
        placeholder="Write your content here. Markdown is supported..."
        @input="updateValue"
      ></textarea>
      <span class="hint">Supports Markdown formatting</span>
    </div>
  </div>
</template>

<style scoped>
.text-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text);
}

.form-group textarea {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  line-height: 1.6;
}

.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}
</style>
