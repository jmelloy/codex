<template>
  <div class="dashboard-view p-6">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-2xl font-semibold text-text-primary">
        {{ definition?.title }}
      </h2>
      <p v-if="definition?.description" class="text-text-secondary mt-1">
        {{ definition.description }}
      </p>
    </div>

    <!-- Dashboard Grid -->
    <div class="space-y-4">
      <div
        v-for="(row, rowIndex) in definition?.layout"
        :key="rowIndex"
        class="dashboard-row grid grid-cols-12 gap-4"
      >
        <div
          v-for="(component, compIndex) in row.components"
          :key="compIndex"
          class="dashboard-component"
          :class="`col-span-${component.span || 12}`"
        >
          <MiniViewContainer
            v-if="component.type === 'mini-view'"
            :view-path="component.view"
            :workspace-id="workspaceId"
            :span="component.span || 12"
            @select-file="(file: any) => emit('selectFile', file)"
          />
          <div v-else class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p class="text-yellow-700">Unknown component type: {{ component.type }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="!definition?.layout || definition.layout.length === 0"
      class="text-center py-12 text-text-tertiary"
    >
      <div class="text-4xl mb-2">📊</div>
      <div class="text-lg">No dashboard layout defined</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import MiniViewContainer from "./MiniViewContainer.vue"
import type { ViewDefinition } from "@/services/viewParser"
import type { QueryResult } from "@/services/queryService"

const props = defineProps<{
  data: QueryResult | null
  config: Record<string, any>
  definition?: ViewDefinition
  workspaceId: number
}>()

const emit = defineEmits<{
  (e: "selectFile", file: any): void
}>()
</script>

<style scoped>
.dashboard-row {
  min-height: 200px;
}

.dashboard-component {
  transition: all 0.3s;
}
</style>
