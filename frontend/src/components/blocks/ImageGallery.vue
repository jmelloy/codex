<template>
  <div class="gallery-block custom-block" :style="{ gridTemplateColumns: `repeat(${columns ?? 3}, 1fr)` }">
    <figure v-for="(img, i) in items" :key="i">
      <img :src="img.src" :alt="img.alt" loading="lazy" />
      <figcaption v-if="img.caption">{{ img.caption }}</figcaption>
    </figure>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { isScriptUrl } from "../../services/mdxRenderer"
import { resolveFileUrl } from "../../utils/markdownHelpers"

const props = defineProps<{
  images: unknown
  columns?: number
  workspaceId?: string
  notebookId?: string
}>()

const items = computed(() => {
  if (!Array.isArray(props.images)) return []
  return props.images
    .map((i) => ({
      src: String(i?.src ?? ""),
      alt: String(i?.alt ?? ""),
      caption: i?.caption ? String(i.caption) : "",
    }))
    .filter((i) => i.src && !isScriptUrl(i.src))
    .map((i) => ({ ...i, src: resolveFileUrl(i.src, props.workspaceId, props.notebookId) }))
})
</script>

<style scoped>
.gallery-block { display: grid; gap: var(--spacing-md); margin: var(--spacing-md) 0; }
.gallery-block img { width: 100%; border-radius: var(--radius-md); }
.gallery-block figcaption { font-size: var(--text-sm); color: var(--color-text-secondary); }
</style>
