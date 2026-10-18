<!-- Renders a single block's MDX content inline, with none of MdxViewer's
     page-level chrome (toolbar/frontmatter/padding) — for use inside
     BlockView.vue's block list, where each block already has its own
     gutter/editing controls. -->
<template>
  <component :is="renderRoot" />
</template>

<script setup lang="ts">
import { useMdxRenderRoot } from "../../composables/useMdxContent"
import type { MdxFormat } from "../../services/mdxRenderer"

interface Props {
  content: string
  format?: MdxFormat
  workspaceId?: string
  notebookId?: string
  parentBlockId?: string
}

const props = withDefaults(defineProps<Props>(), {
  format: "mdx",
  workspaceId: undefined,
  notebookId: undefined,
  parentBlockId: undefined,
})

const renderRoot = useMdxRenderRoot(
  () => props.content,
  () => ({
    workspaceId: props.workspaceId,
    notebookId: props.notebookId,
    parentBlockId: props.parentBlockId,
  }),
  () => props.format,
)
</script>
