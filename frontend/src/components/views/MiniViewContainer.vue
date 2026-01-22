<template>
  <div class="mini-view-container bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center h-48">
      <div class="text-gray-400 text-sm">Loading...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="p-4 bg-red-50">
      <p class="text-red-600 text-sm">{{ error }}</p>
    </div>

    <!-- View Renderer -->
    <ViewRenderer
      v-else-if="viewFileId"
      :file-id="viewFileId"
      :workspace-id="workspaceId"
      :compact="true"
    />

    <!-- Not Found State -->
    <div v-else class="p-4 bg-yellow-50">
      <p class="text-yellow-700 text-sm">View not found: {{ viewPath }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import ViewRenderer from './ViewRenderer.vue';
import { fileService, notebookService } from '@/services/codex';

const props = defineProps<{
  viewPath: string;
  workspaceId: number;
  span: number;
}>();

const viewFileId = ref<number | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

/**
 * Resolve view path to file ID
 * The viewPath can be:
 * - Relative path like "tasks/today.cdx"
 * - Absolute path like "/notebook/tasks/today.cdx"
 */
const resolveViewPath = async () => {
  loading.value = true;
  error.value = null;

  try {
    // Get all notebooks in workspace
    const notebooks = await notebookService.list(props.workspaceId);

    // Search through notebooks for the file
    for (const notebook of notebooks) {
      try {
        const files = await fileService.list(notebook.id, props.workspaceId);

        // Look for file matching the path
        const matchingFile = files.find((file) => {
          // Check if the file path ends with the view path
          return (
            file.path === props.viewPath ||
            file.path.endsWith('/' + props.viewPath) ||
            file.path.endsWith(props.viewPath)
          );
        });

        if (matchingFile) {
          viewFileId.value = matchingFile.id;
          return;
        }
      } catch (err) {
        console.warn(`Failed to search notebook ${notebook.id}:`, err);
      }
    }

    error.value = `View file not found: ${props.viewPath}`;
  } catch (err: any) {
    error.value = `Failed to resolve view path: ${err.message}`;
  } finally {
    loading.value = false;
  }
};

// Resolve path when component mounts or viewPath changes
watch(() => props.viewPath, resolveViewPath, { immediate: true });
</script>

<style scoped>
.mini-view-container {
  height: 100%;
  min-height: 200px;
}
</style>
