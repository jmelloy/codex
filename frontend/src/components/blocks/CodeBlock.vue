<template>
  <CodeViewer :content="content" :language="language" :filename="filename" />
</template>

<script setup lang="ts">
import { computed, useSlots } from "vue"
import CodeViewer from "../CodeViewer.vue"
import { flattenChildrenToText } from "../../services/mdxRenderer"

interface Props {
  language?: string
  filename?: string
  // Accepted for parity with common MDX/rehype-pretty-code conventions.
  mdxChildren?: string
}

const props = defineProps<Props>()
const slots = useSlots()

const content = computed(() => {
  if (props.mdxChildren !== undefined) return props.mdxChildren
  return flattenChildrenToText(slots.default?.())
})
</script>
