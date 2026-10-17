<!-- Renders a single block's MDX content inline, with none of MdxViewer's
     page-level chrome (toolbar/frontmatter/padding) — for use inside
     BlockView.vue's block list, where each block already has its own
     gutter/editing controls. -->
<template>
  <component :is="renderRoot" />
</template>

<script setup lang="ts">
import { useMdxRenderRoot } from "../../composables/useMdxContent"

interface Props {
  content: string
  workspaceId?: string
  notebookId?: string
  parentBlockId?: string
}

const props = withDefaults(defineProps<Props>(), {
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
)
</script>
