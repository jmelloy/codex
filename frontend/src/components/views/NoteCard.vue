<template>
  <div class="note-card-content p-4">
    <!-- Pin -->
    <div class="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-red-500 shadow-md"></div>

    <!-- Title -->
    <h4 class="font-bold text-text-primary mb-2 text-sm line-clamp-2">
      {{ file.title || file.filename }}
    </h4>

    <!-- Card Fields -->
    <div v-if="config.card_fields" class="space-y-1 text-xs">
      <div v-for="field in config.card_fields" :key="field" v-show="getFieldValue(field)">
        <span class="font-semibold text-text-primary capitalize">{{ field }}:</span>
        <span class="text-text-secondary ml-1">{{ formatValue(getFieldValue(field)) }}</span>
      </div>
    </div>

    <!-- Description -->
    <p v-if="file.description" class="text-xs text-text-secondary mt-2 line-clamp-3">
      {{ file.description }}
    </p>

    <!-- Tags -->
    <div v-if="file.properties?.tags" class="flex flex-wrap gap-1 mt-2">
      <span
        v-for="tag in file.properties.tags.slice(0, 3)"
        :key="tag"
        class="px-1.5 py-0.5 text-xs bg-black/10 rounded"
      >
        {{ tag }}
      </span>
      <span v-if="file.properties.tags.length > 3" class="text-xs text-text-tertiary">
        +{{ file.properties.tags.length - 3 }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FileMetadata } from '@/services/codex';
import type { CorkboardConfig } from '@/services/viewParser';

const props = defineProps<{
  file: FileMetadata;
  config: CorkboardConfig;
}>();

const getFieldValue = (field: string): any => {
  if (field === 'title') return props.file.title;
  if (field === 'description') return props.file.description;
  return props.file.properties?.[field];
};

const formatValue = (value: any): string => {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};
</script>

<style scoped>
.note-card-content {
  position: relative;
  min-height: 150px;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
