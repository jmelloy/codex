<template>
  <div class="view-renderer">
    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="text-text-tertiary">Loading view...</div>
    </div>

    <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
      <h3 class="text-red-800 font-semibold mb-2">Error loading view</h3>
      <p class="text-red-600">{{ error }}</p>
    </div>

    <component
      v-else-if="viewComponent"
      :is="viewComponent"
      :data="queryResults"
      :config="viewConfig"
      :definition="viewDefinition"
      :workspace-id="workspaceId"
      @update="handleUpdate"
      @refresh="loadView"
      @select-file="(file: any) => emit('selectFile', file)"
    />

    <div v-else class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
      <h3 class="text-yellow-800 font-semibold mb-2">Unknown view type</h3>
      <p class="text-yellow-600">View type "{{ viewDefinition?.view_type }}" is not supported.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, shallowRef } from "vue"
import { parseViewDefinition, type ViewDefinition } from "@/services/viewParser"
import { queryService, type QueryResult } from "@/services/queryService"
import { fileService } from "@/services/codex"
import { viewPluginService } from "@/services/viewPluginService"

const props = defineProps<{
  fileId: number
  workspaceId: number
  notebookId: number
  compact?: boolean // For mini-views
}>()

const emit = defineEmits<{
  (e: "error", error: string): void
  (e: "loaded", definition: ViewDefinition): void
  (e: "selectFile", file: any): void
}>()

const loading = ref(true)
const error = ref<string | null>(null)
const viewDefinition = ref<ViewDefinition | null>(null)
const queryResults = ref<QueryResult | null>(null)
const viewComponent = shallowRef<any>(null)

// Load view definition and execute query
const loadView = async () => {
  loading.value = true
  error.value = null

  try {
    // Load file metadata first
    const file = await fileService.get(props.fileId, props.workspaceId, props.notebookId)

    // Fetch content when not included in metadata
    let content = (file as { content?: string }).content
    if (content === undefined) {
      const textContent = await fileService.getContent(
        props.fileId,
        props.workspaceId,
        props.notebookId,
      )
      content = textContent.content
    }

    // Parse view definition
    viewDefinition.value = parseViewDefinition(content || "")

    // Execute query if defined
    if (viewDefinition.value.query) {
      queryResults.value = await queryService.execute(props.workspaceId, viewDefinition.value.query)
    }

    emit("loaded", viewDefinition.value)
  } catch (err: any) {
    error.value = err.message || "Failed to load view"
    emit("error", error.value as string)
  } finally {
    loading.value = false
  }
}

// Map view type to component using plugin service
watch(
  () => viewDefinition.value?.view_type,
  async (viewType) => {
    if (!viewType) {
      viewComponent.value = null
      return
    }

    try {
      // Ensure plugin service is initialized before checking
      await viewPluginService.initialize()

      // Try to load component from plugin service
      if (viewPluginService.hasViewComponent(viewType)) {
        viewComponent.value = await viewPluginService.loadViewComponent(viewType)
      } else {
        // View type exists in definition but component not registered
        console.warn(`View component not found for type: ${viewType}. Available: ${viewPluginService.getValidViewTypes().join(", ") || "none"}`)
        viewComponent.value = null
      }
    } catch (err) {
      console.error("Failed to load view component:", err)
      viewComponent.value = null
    }
  },
  { immediate: true },
)

const viewConfig = computed(() => viewDefinition.value?.config || {})

// Handle update events from views (e.g., drag-drop)
interface ViewUpdateEvent {
  fileId: number
  updates: Record<string, any>
}

const handleUpdate = async (event: ViewUpdateEvent) => {
  try {
    // Load current file metadata
    const file = await fileService.get(event.fileId, props.workspaceId, props.notebookId)

    // Fetch content when not included in metadata
    let content = (file as { content?: string }).content
    if (content === undefined) {
      const textContent = await fileService.getContent(
        event.fileId,
        props.workspaceId,
        props.notebookId,
      )
      content = textContent.content
    }

    // Merge updates into properties
    const updatedProperties = {
      ...(file.properties || {}),
      ...event.updates,
    }

    // Update file
    await fileService.update(
      event.fileId,
      props.workspaceId,
      file.notebook_id ?? props.notebookId,
      content || "",
      updatedProperties,
    )

    // Refresh view
    await loadView()
  } catch (err: any) {
    error.value = `Failed to update file: ${err.message}`
  }
}

// Load view when component mounts or fileId changes
watch(() => props.fileId, loadView, { immediate: true })
</script>

<style scoped>
.view-renderer {
  width: 100%;
  height: 100%;
  overflow: auto;
}
</style>
