<template>
  <div class="template-selector">
    <div class="space-y-2">
      <!-- Blank File option -->
      <div
        :class="[
          'template-item flex items-center gap-3 p-3 rounded-md cursor-pointer transition border',
          createMode === 'file'
            ? 'border-primary bg-primary/10'
            : 'border-border-light hover:border-border-medium hover:bg-bg-hover',
        ]"
        @click="selectMode('file')"
      >
        <span class="text-2xl">📄</span>
        <div class="flex-1 min-w-0">
          <div class="font-medium text-text-primary">Blank File</div>
          <div class="text-sm text-text-secondary truncate">
            Create an empty file with custom name
          </div>
        </div>
        <div
          v-if="createMode === 'file'"
          class="w-5 h-5 rounded-full bg-primary flex items-center justify-center"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
      </div>

      <!-- Templates section -->
      <div class="flex items-center gap-2 py-2">
        <div class="flex-1 h-px bg-border-light"></div>
        <span class="text-xs text-text-tertiary uppercase">Templates</span>
        <div class="flex-1 h-px bg-border-light"></div>
      </div>

      <!-- Loading state for templates -->
      <div v-if="loading" class="flex items-center justify-center py-4">
        <span class="text-sm text-text-secondary">Loading templates...</span>
      </div>

      <!-- Error state for templates -->
      <div v-else-if="error" class="text-sm text-text-secondary text-center py-2">
        Could not load templates
      </div>

      <!-- No templates available -->
      <div v-else-if="filteredTemplates.length === 0" class="text-sm text-text-secondary text-center py-2">
        No templates available
      </div>

      <!-- Template items -->
      <template v-else>
        <div
          v-for="template in filteredTemplates"
          :key="template.id"
          :class="[
            'template-item flex items-center gap-3 p-3 rounded-md cursor-pointer transition border',
            selectedTemplate?.id === template.id
              ? 'border-primary bg-primary/10'
              : 'border-border-light hover:border-border-medium hover:bg-bg-hover',
          ]"
          @click="selectTemplate(template)"
        >
          <span class="text-2xl">{{ template.icon }}</span>
          <div class="flex-1 min-w-0">
            <div class="font-medium text-text-primary flex items-center gap-2">
              {{ template.name }}
              <span
                v-if="template.source === 'notebook'"
                class="text-xs px-1.5 py-0.5 bg-primary/20 text-primary rounded"
              >
                Custom
              </span>
            </div>
            <div class="text-sm text-text-secondary truncate">
              {{ template.description }}
            </div>
            <div class="text-xs text-text-tertiary mt-1">
              {{ expandedFilename(template) }}
            </div>
          </div>
          <div
            v-if="selectedTemplate?.id === template.id"
            class="w-5 h-5 rounded-full bg-primary flex items-center justify-center"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
        </div>
      </template>
    </div>

    <!-- Filter by type -->
    <div v-if="templates.length > 0" class="mt-4 flex items-center gap-2">
      <span class="text-sm text-text-secondary">Filter:</span>
      <button
        v-for="ext in availableExtensions"
        :key="ext"
        :class="[
          'px-2 py-1 text-xs rounded transition',
          filterExtension === ext
            ? 'bg-primary text-white'
            : 'bg-bg-hover text-text-secondary hover:bg-bg-tertiary',
        ]"
        @click="filterExtension = filterExtension === ext ? null : ext"
      >
        {{ ext || "All" }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue"
import { templateService, type Template } from "../services/codex"

const props = defineProps<{
  notebookId?: number
  workspaceId?: number
  modelValue?: Template | null
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: Template | null): void
  (e: "select", template: Template | null): void
  (e: "update:mode", value: "file" | "template"): void
}>()

const templates = ref<Template[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedTemplate = ref<Template | null>(props.modelValue || null)
const createMode = ref<"file" | "template">("file")
const filterExtension = ref<string | null>(null)

// Get unique file extensions from templates
const availableExtensions = computed(() => {
  const extensions = new Set<string>()
  templates.value.forEach((t) => extensions.add(t.file_extension))
  return Array.from(extensions).sort()
})

// Filter templates by extension
const filteredTemplates = computed(() => {
  if (!filterExtension.value) {
    return templates.value
  }
  return templates.value.filter((t) => t.file_extension === filterExtension.value)
})

// Expand the default filename pattern for preview
function expandedFilename(template: Template): string {
  return templateService.expandPattern(template.default_name, "untitled")
}

function selectMode(mode: "file") {
  createMode.value = mode
  selectedTemplate.value = null
  emit("update:modelValue", null)
  emit("select", null)
  emit("update:mode", mode)
}

function selectTemplate(template: Template | null) {
  selectedTemplate.value = template
  createMode.value = template ? "template" : "file"
  emit("update:modelValue", template)
  emit("select", template)
  emit("update:mode", template ? "template" : "file")
}

async function fetchTemplates() {
  if (!props.notebookId || !props.workspaceId) return
  loading.value = true
  error.value = null
  try {
    templates.value = await templateService.list(props.notebookId, props.workspaceId)
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to load templates"
  } finally {
    loading.value = false
  }
}

// Fetch templates when notebook changes
watch(
  () => [props.notebookId, props.workspaceId],
  () => {
    if (props.notebookId && props.workspaceId) {
      fetchTemplates()
    }
  },
  { immediate: true }
)

// Sync external model value
watch(
  () => props.modelValue,
  (newVal) => {
    selectedTemplate.value = newVal || null
  }
)

onMounted(() => {
  if (props.notebookId && props.workspaceId) {
    fetchTemplates()
  }
})
</script>

<style scoped>
.template-selector {
  max-height: 400px;
  overflow-y: auto;
}

.template-item {
  user-select: none;
}
</style>
