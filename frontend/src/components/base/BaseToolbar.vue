<template>
  <div class="base-toolbar" :class="themeClass">
    <div class="toolbar-section left">
      <slot name="left"></slot>
    </div>
    <div class="toolbar-section center">
      <slot name="center"></slot>
    </div>
    <div class="toolbar-section right">
      <slot name="right"></slot>
    </div>
    <!-- Default slot for backward compatibility -->
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
interface Props {
  theme?: 'light' | 'dark' | 'auto'
}

const props = withDefaults(defineProps<Props>(), {
  theme: 'auto'
})

const themeClass = props.theme === 'auto' ? '' : `toolbar-${props.theme}`
</script>

<style scoped>
.base-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--toolbar-bg, var(--bg-primary));
  border-bottom: 1px solid var(--border-light, var(--border-medium));
  flex-wrap: wrap;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toolbar-section.left {
  flex: 0 0 auto;
}

.toolbar-section.center {
  flex: 1 1 auto;
  justify-content: center;
}

.toolbar-section.right {
  flex: 0 0 auto;
  margin-left: auto;
}

/* Button styling for toolbar items */
.base-toolbar :deep(button) {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border-medium);
  border-radius: 0.375rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
}

.base-toolbar :deep(button:hover) {
  background: var(--bg-hover);
}

.base-toolbar :deep(button:active),
.base-toolbar :deep(button.active) {
  background: var(--bg-active, var(--bg-hover));
  border-color: var(--border-dark, var(--border-medium));
}

.base-toolbar :deep(button:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
