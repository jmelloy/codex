<template>
  <div class="embed-block custom-block">
    <iframe
      v-if="url"
      :src="url"
      :title="title || `${provider} embed`"
      :height="height"
      sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
      referrerpolicy="no-referrer"
      loading="lazy"
      allowfullscreen
    />
    <div v-else class="embed-error">Invalid {{ provider }} id: {{ id }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { buildEmbedUrl } from "../../services/mdxEmbed"

const props = defineProps<{ provider: string; id: string; title?: string; height?: number }>()
const url = computed(() => buildEmbedUrl(props.provider, props.id))
</script>

<style scoped>
.embed-block iframe { width: 100%; border: 0; border-radius: var(--radius-md); }
.embed-error { color: var(--color-error); font-size: var(--text-sm); }
</style>
