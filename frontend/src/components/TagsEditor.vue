<template>
  <div class="property-section">
    <h4>Tags</h4>
    <div class="tags-list">
      <span v-for="tag in tags" :key="tag" class="tag">
        {{ tag }}
        <button @click="emit('remove', tag)" class="tag-remove" title="Remove tag">×</button>
      </span>
    </div>
    <div class="tag-input-wrapper">
      <input
        v-model="newTagModel"
        @keyup.enter="emit('add')"
        class="tag-input"
        placeholder="Add a tag..."
      />
      <button @click="emit('add')" class="tag-add-btn" :disabled="!newTagModel.trim()">Add</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  tags: string[]
}>()

const newTagModel = defineModel<string>("newTag", { default: "" })

const emit = defineEmits<{
  add: []
  remove: [tag: string]
}>()
</script>

<style scoped>
.property-section {
  margin-bottom: var(--spacing-xl);
}

.property-section h4 {
  margin: 0 0 var(--spacing-md);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.tag-remove {
  background: none;
  border: none;
  color: var(--color-text-placeholder);
  cursor: pointer;
  padding: 0;
  line-height: 1;
  font-size: var(--text-sm);
  transition: color 0.2s;
}

.tag-remove:hover {
  color: var(--color-error);
}

.tag-input-wrapper {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.tag-input {
  flex: 1;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 0.2s;
}

.tag-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
}

.tag-add-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background 0.2s;
}

.tag-add-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.tag-add-btn:disabled {
  background: var(--color-bg-disabled);
  color: var(--color-text-disabled);
  cursor: not-allowed;
}
</style>
