<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { marked } from "marked";

const props = defineProps<{
  content: string;
  placeholder?: string;
  editable?: boolean;
}>();

const emit = defineEmits<{
  (e: "update", content: string): void;
}>();

const isEditing = ref(false);
const editContent = ref(props.content);
const textareaRef = ref<HTMLTextAreaElement | null>(null);

const renderedHtml = computed(() => {
  if (!props.content) return "";
  return marked(props.content);
});

watch(() => props.content, (newContent) => {
  editContent.value = newContent;
});

function startEditing() {
  if (!props.editable) return;
  isEditing.value = true;
  editContent.value = props.content;
  setTimeout(() => {
    textareaRef.value?.focus();
    autoResize();
  }, 0);
}

function finishEditing() {
  isEditing.value = false;
  if (editContent.value !== props.content) {
    emit("update", editContent.value);
  }
}

function autoResize() {
  if (textareaRef.value) {
    textareaRef.value.style.height = "auto";
    textareaRef.value.style.height = textareaRef.value.scrollHeight + "px";
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    editContent.value = props.content;
    isEditing.value = false;
  }
}
</script>

<template>
  <div class="text-block" :class="{ editable, editing: isEditing }">
    <div
      v-if="!isEditing"
      class="text-content"
      :class="{ empty: !content }"
      @click="startEditing"
      v-html="renderedHtml || placeholder || 'Click to add text...'"
    />
    <textarea
      v-else
      ref="textareaRef"
      v-model="editContent"
      class="text-editor"
      :placeholder="placeholder"
      @blur="finishEditing"
      @keydown="handleKeydown"
      @input="autoResize"
    />
  </div>
</template>

<style scoped>
.text-block {
  position: relative;
  min-height: 1.5rem;
}

.text-block.editable:hover .text-content {
  background: var(--color-background);
  border-radius: var(--radius-sm);
}

.text-content {
  padding: 0.5rem;
  cursor: text;
  line-height: 1.6;
}

.text-content.empty {
  color: var(--color-text-secondary);
  font-style: italic;
}

.text-content :deep(h1),
.text-content :deep(h2),
.text-content :deep(h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.text-content :deep(h1:first-child),
.text-content :deep(h2:first-child),
.text-content :deep(h3:first-child) {
  margin-top: 0;
}

.text-content :deep(p) {
  margin-bottom: 0.75rem;
}

.text-content :deep(p:last-child) {
  margin-bottom: 0;
}

.text-content :deep(ul),
.text-content :deep(ol) {
  margin-left: 1.5rem;
  margin-bottom: 0.75rem;
}

.text-content :deep(code) {
  background: var(--color-background);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
  font-size: 0.875em;
}

.text-content :deep(pre) {
  background: var(--color-background);
  padding: 1rem;
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin-bottom: 0.75rem;
}

.text-content :deep(pre code) {
  background: none;
  padding: 0;
}

.text-content :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 1rem;
  margin: 0.75rem 0;
  color: var(--color-text-secondary);
}

.text-editor {
  width: 100%;
  min-height: 80px;
  padding: 0.5rem;
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: inherit;
  line-height: 1.6;
  resize: none;
  outline: none;
  background: var(--color-surface);
}
</style>
