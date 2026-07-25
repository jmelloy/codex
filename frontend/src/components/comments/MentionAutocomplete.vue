<template>
  <ul v-if="principals.length > 0" class="mention-autocomplete" role="listbox">
    <li
      v-for="(principal, index) in principals"
      :key="principal.id"
      class="mention-option"
      :class="{ active: index === activeIndex }"
      role="option"
      @mousedown.prevent="$emit('select', principal)"
      @mouseenter="activeIndex = index"
    >
      <span class="mention-at">@</span>{{ principal.username }}
    </li>
  </ul>
  <div v-else class="mention-autocomplete mention-empty">No matching members</div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"
import type { Principal } from "../../services/comments"

const props = defineProps<{
  principals: Principal[]
}>()

const emit = defineEmits<{
  select: [principal: Principal]
}>()

const activeIndex = ref(0)

watch(
  () => props.principals,
  () => {
    activeIndex.value = 0
  },
)

/** Move the highlighted option; called by the composer on ArrowUp/ArrowDown. */
function move(delta: number) {
  if (props.principals.length === 0) return
  const next = (activeIndex.value + delta + props.principals.length) % props.principals.length
  activeIndex.value = next
}

/** Confirm the currently highlighted option; called by the composer on Enter/Tab. */
function confirmActive() {
  const principal = props.principals[activeIndex.value]
  if (principal) emit("select", principal)
}

defineExpose({ move, confirmActive })
</script>

<style scoped>
.mention-autocomplete {
  position: absolute;
  z-index: 40;
  min-width: 180px;
  max-height: 220px;
  overflow-y: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-light, #e0e0e0);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.mention-empty {
  padding: 8px 10px;
  font-size: 0.8125rem;
  color: var(--color-text-tertiary, #999);
}

.mention-option {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.8125rem;
  color: var(--color-text-primary, #333);
  cursor: pointer;
}

.mention-option.active,
.mention-option:hover {
  background: var(--color-bg-hover, #f5f5f5);
}

.mention-at {
  color: var(--color-text-tertiary, #999);
}
</style>
