<template>
  <div class="kanban-view p-6">
    <div class="flex gap-4 overflow-x-auto pb-4">
      <div
        v-for="column in columns"
        :key="column.id"
        class="kanban-column flex-shrink-0 bg-bg-hover rounded-lg p-4 min-w-[300px]"
      >
        <!-- Column Header -->
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-semibold text-text-primary">
            {{ column.title }}
          </h3>
          <span class="text-sm text-text-tertiary">
            {{ getColumnCards(column.id).length }}
          </span>
        </div>

        <!-- Drop Zone -->
        <div
          class="kanban-cards space-y-3 min-h-[200px]"
          :data-column-id="column.id"
          @dragover.prevent="handleDragOver"
          @drop="handleDrop($event, column.id)"
        >
          <!-- Cards -->
          <div
            v-for="card in getColumnCards(column.id)"
            :key="card.id"
            :draggable="config.drag_drop !== false"
            class="kanban-card bg-white rounded-md shadow-sm p-3 border border-border-light cursor-move hover:shadow-md transition"
            :data-file-id="card.id"
            @dragstart="handleDragStart($event, card)"
            @click="handleCardClick(card)"
          >
            <!-- Card Title -->
            <div class="font-medium text-text-primary mb-2">
              {{ card.title || card.filename }}
            </div>

            <!-- Card Fields -->
            <div v-if="config.card_fields" class="space-y-1 text-sm">
              <div
                v-for="field in config.card_fields"
                :key="field"
                v-show="getCardField(card, field)"
                class="text-text-secondary"
              >
                <span class="font-medium capitalize">{{ field }}:</span>
                {{ formatFieldValue(getCardField(card, field)) }}
              </div>
            </div>

            <!-- Tags -->
            <div v-if="card.properties?.tags" class="flex flex-wrap gap-1 mt-2">
              <span
                v-for="tag in card.properties.tags"
                :key="tag"
                class="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
              >
                {{ tag }}
              </span>
            </div>
          </div>

          <!-- Empty State -->
          <div
            v-if="getColumnCards(column.id).length === 0"
            class="text-center py-8 text-text-tertiary text-sm"
          >
            Drop cards here
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import type { KanbanConfig } from "@/services/viewParser"
import type { QueryResult } from "@/services/queryService"
import type { FileMetadata } from "@/services/codex"

const props = defineProps<{
  data: QueryResult | null
  config: KanbanConfig
  workspaceId: number
}>()

const emit = defineEmits<{
  (e: "update", event: { fileId: number; updates: Record<string, any> }): void
  (e: "refresh"): void
  (e: "selectFile", file: FileMetadata): void
}>()

const draggedCard = ref<FileMetadata | null>(null)

// Get columns from config
const columns = computed(() => props.config.columns || [])

// Get files for a specific column
const getColumnCards = (columnId: string) => {
  if (!props.data?.files) return []

  const column = columns.value.find((c) => c.id === columnId)
  if (!column) return []

  // Filter files based on column filter
  if (column.filter) {
    return props.data.files.filter((file) => {
      if (!file.properties) return false

      // Check if all filter conditions match
      return Object.entries(column.filter || {}).every(([key, value]) => {
        return file.properties?.[key] === value
      })
    })
  }

  return props.data.files
}

// Get field value from card
const getCardField = (card: FileMetadata, field: string) => {
  // Check direct properties
  if (field === "title") return card.title
  if (field === "description") return card.description
  if (field === "filename") return card.filename

  // Check properties object
  return card.properties?.[field]
}

// Format field value for display
const formatFieldValue = (value: any): string => {
  if (value === null || value === undefined) return ""
  if (Array.isArray(value)) return value.join(", ")
  if (typeof value === "object") return JSON.stringify(value)
  if (typeof value === "boolean") return value ? "Yes" : "No"
  return String(value)
}

// Drag and drop handlers
const handleDragStart = (event: DragEvent, card: FileMetadata) => {
  draggedCard.value = card
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move"
    event.dataTransfer.setData("text/plain", String(card.id))
  }
}

const handleDragOver = (event: DragEvent) => {
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move"
  }
}

const handleDrop = (event: DragEvent, columnId: string) => {
  event.preventDefault()

  if (!draggedCard.value || !props.config.drag_drop) return

  const targetColumn = columns.value.find((c) => c.id === columnId)
  if (!targetColumn || !targetColumn.filter) return

  // Update the card's properties based on column filter
  const updates = { ...targetColumn.filter }

  emit("update", {
    fileId: draggedCard.value.id,
    updates,
  })

  draggedCard.value = null
}

// Handle card click
const handleCardClick = (card: FileMetadata) => {
  // Emit event to select the file
  emit("selectFile", card)
}
</script>

<style scoped>
.kanban-view {
  height: 100%;
  overflow: auto;
}

.kanban-column {
  width: 300px;
}

.kanban-card {
  transition: all 0.2s;
}

.kanban-card:hover {
  transform: translateY(-2px);
}

.kanban-card:active {
  cursor: grabbing;
  opacity: 0.7;
}
</style>
