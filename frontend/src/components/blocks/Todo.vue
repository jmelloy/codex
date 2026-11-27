<template>
  <ul class="todo-block custom-block">
    <li v-for="(item, i) in list" :key="i" :class="{ done: item.done }">
      <input type="checkbox" :checked="item.done" disabled :aria-label="item.text" />
      <span>{{ item.text }}</span>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { computed, useSlots } from "vue"
import { flattenChildrenToText } from "../../services/mdxRenderer"

const props = defineProps<{ items?: unknown }>()
const slots = useSlots()

interface TodoItem { text: string; done: boolean }

// Items come from the `items` JSON prop, or from children lines like "[x] done" / "[ ] open".
const list = computed<TodoItem[]>(() => {
  if (Array.isArray(props.items)) {
    return props.items.map((it) =>
      typeof it === "string"
        ? { text: it, done: false }
        : { text: String(it?.text ?? ""), done: Boolean(it?.done) },
    )
  }
  return flattenChildrenToText(slots.default?.())
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const m = l.match(/^(?:[-*]\s*)?\[([ xX])\]\s*(.*)$/)
      return m ? { text: m[2], done: m[1] !== " " } : { text: l, done: false }
    })
})
</script>

<style scoped>
.todo-block { list-style: none; padding: 0; margin: var(--spacing-md) 0; }
.todo-block li { display: flex; gap: var(--spacing-sm); align-items: center; }
.todo-block li.done span { text-decoration: line-through; color: var(--color-text-secondary); }
</style>
