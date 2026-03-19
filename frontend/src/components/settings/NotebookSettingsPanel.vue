<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <h1 class="panel-title">Notebook Configuration</h1>
      <p class="panel-subtitle">{{ notebookName }}</p>
    </div>

    <div class="panel-content">
      <section class="config-section">
        <h3 class="section-heading">Plugins</h3>
        <p class="section-description">
          Plugins (themes and integrations) are managed via the backend plugins directory.
        </p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWorkspaceStore } from '../../stores/workspace'

const props = defineProps<{
  workspaceId: number
  notebookId: number
}>()

const workspaceStore = useWorkspaceStore()

const notebookName = computed(() => {
  const nb = workspaceStore.notebooks.find(n => n.id === props.notebookId)
  return nb?.name || 'Notebook'
})
</script>

<style src="./settings-panel.css"></style>
