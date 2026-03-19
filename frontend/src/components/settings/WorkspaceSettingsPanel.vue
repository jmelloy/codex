<template>
  <div class="panel-wrapper">
    <div class="panel-header">
      <h1 class="panel-title">Workspace Configuration</h1>
      <p class="panel-subtitle">{{ workspaceName }}</p>
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
}>()

const workspaceStore = useWorkspaceStore()

const workspaceName = computed(() => {
  const ws = workspaceStore.workspaces.find(w => w.id === props.workspaceId)
  return ws?.name || 'Workspace'
})
</script>

<style src="./settings-panel.css"></style>
