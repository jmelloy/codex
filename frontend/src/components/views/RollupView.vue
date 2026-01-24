<template>
  <div class="rollup-view p-6">
    <!-- Header -->
    <div class="mb-6">
      <h2 class="text-2xl font-semibold text-text-primary">{{ definition?.title }}</h2>
      <p v-if="definition?.description" class="text-text-secondary mt-1">
        {{ definition.description }}
      </p>
    </div>

    <!-- Statistics -->
    <div v-if="config.show_stats" class="grid grid-cols-3 gap-4 mb-6">
      <div class="bg-blue-50 rounded-lg p-4">
        <div class="text-2xl font-bold text-blue-600">{{ totalFiles }}</div>
        <div class="text-sm text-blue-700">Total Items</div>
      </div>
      <div class="bg-green-50 rounded-lg p-4">
        <div class="text-2xl font-bold text-green-600">{{ uniqueDates }}</div>
        <div class="text-sm text-green-700">Days</div>
      </div>
      <div class="bg-purple-50 rounded-lg p-4">
        <div class="text-2xl font-bold text-purple-600">{{ uniqueTags }}</div>
        <div class="text-sm text-purple-700">Tags</div>
      </div>
    </div>

    <!-- Grouped Content -->
    <div class="space-y-6">
      <div v-for="(group, date) in groupedFiles" :key="date" class="rollup-group">
        <!-- Date Header -->
        <div class="flex items-center gap-3 mb-3">
          <button
            class="flex items-center gap-2 text-lg font-semibold text-text-primary hover:text-text-secondary"
            @click="toggleGroup(date)"
          >
            <span class="text-sm">{{ isGroupExpanded(date) ? '▼' : '▶' }}</span>
            {{ formatGroupDate(date) }}
          </button>
          <span class="text-sm text-text-tertiary">{{ group.length }} items</span>
        </div>

        <!-- Group Content -->
        <div v-if="isGroupExpanded(date)" class="pl-6 space-y-3">
          <!-- Sections (if configured) -->
          <template v-if="config.sections">
            <div
              v-for="section in config.sections"
              :key="section.title"
              class="mb-4"
            >
              <h4 class="text-sm font-semibold text-text-primary mb-2">
                {{ section.title }}
              </h4>
              <div class="space-y-2">
                <div
                  v-for="file in filterSection(group, section)"
                  :key="file.id"
                  class="bg-white rounded-lg border border-border-light p-3 hover:shadow-md transition cursor-pointer"
                  @click="handleFileClick(file)"
                >
                  <div class="font-medium text-text-primary">
                    {{ file.title || file.filename }}
                  </div>
                  <div v-if="file.description" class="text-sm text-text-secondary mt-1">
                    {{ file.description }}
                  </div>
                  <div v-if="file.properties?.tags" class="flex flex-wrap gap-1 mt-2">
                    <span
                      v-for="tag in file.properties.tags"
                      :key="tag"
                      class="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
                    >
                      {{ tag }}
                    </span>
                  </div>
                </div>
                <div v-if="filterSection(group, section).length === 0" class="text-sm text-text-tertiary italic">
                  No {{ section.title.toLowerCase() }}
                </div>
              </div>
            </div>
          </template>

          <!-- Default: All files -->
          <template v-else>
            <div
              v-for="file in group"
              :key="file.id"
              class="bg-white rounded-lg border border-border-light p-3 hover:shadow-md transition cursor-pointer"
              @click="handleFileClick(file)"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="font-medium text-text-primary">
                    {{ file.title || file.filename }}
                  </div>
                  <div v-if="file.description" class="text-sm text-text-secondary mt-1">
                    {{ file.description }}
                  </div>
                </div>
                <div class="text-xs text-text-tertiary">
                  {{ formatTime(file.created_at) }}
                </div>
              </div>

              <!-- Tags -->
              <div v-if="file.properties?.tags" class="flex flex-wrap gap-1 mt-2">
                <span
                  v-for="tag in file.properties.tags"
                  :key="tag"
                  class="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="totalFiles === 0" class="text-center py-12 text-text-tertiary">
      <div class="text-4xl mb-2">📊</div>
      <div class="text-lg">No data to display</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { RollupConfig, ViewDefinition } from '@/services/viewParser';
import type { QueryResult } from '@/services/queryService';
import type { FileMetadata } from '@/services/codex';

const props = defineProps<{
  data: QueryResult | null;
  config: RollupConfig;
  definition?: ViewDefinition;
  workspaceId: number;
}>();

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const expandedGroups = ref<Set<string>>(new Set());

// Group files by date
const groupedFiles = computed(() => {
  if (!props.data?.files) return {};

  const groups: Record<string, FileMetadata[]> = {};
  const groupFormat = props.config.group_format || 'day';

  props.data.files.forEach((file) => {
    const dateStr = file.created_at;
    if (!dateStr) return;

    const date = new Date(dateStr);
    let groupKey: string;

    switch (groupFormat) {
      case 'week':
        groupKey = getWeekKey(date);
        break;
      case 'month':
        groupKey = getMonthKey(date);
        break;
      case 'day':
      default:
        groupKey = getDayKey(date);
        break;
    }

    if (!groups[groupKey]) {
      groups[groupKey] = [];
    }
    groups[groupKey]!.push(file);
  });

  // Sort groups by date (most recent first)
  const sortedGroups: Record<string, FileMetadata[]> = {};
  Object.keys(groups)
    .sort((a, b) => b.localeCompare(a))
    .forEach((key) => {
      sortedGroups[key] = groups[key]!;
      // Expand first group by default
      if (Object.keys(sortedGroups).length === 1) {
        expandedGroups.value.add(key);
      }
    });

  return sortedGroups;
});

// Get day key (YYYY-MM-DD)
const getDayKey = (date: Date): string => {
  return date.toISOString().split('T')[0] as string;
};

// Get week key (YYYY-Www)
const getWeekKey = (date: Date): string => {
  const year = date.getFullYear();
  const firstDayOfYear = new Date(year, 0, 1);
  const daysSinceFirstDay = Math.floor(
    (date.getTime() - firstDayOfYear.getTime()) / (1000 * 60 * 60 * 24)
  );
  const weekNumber = Math.ceil((daysSinceFirstDay + firstDayOfYear.getDay() + 1) / 7);
  return `${year}-W${String(weekNumber).padStart(2, '0')}`;
};

// Get month key (YYYY-MM)
const getMonthKey = (date: Date): string => {
  return date.toISOString().substring(0, 7);
};

// Format group date for display
const formatGroupDate = (dateKey: string): string => {
  const format = props.config.group_format || 'day';

  if (format === 'week') {
    const [year, week] = dateKey.split('-W');
    return `Week ${week}, ${year}`;
  } else if (format === 'month') {
    const date = new Date(dateKey + '-01');
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  } else {
    const date = new Date(dateKey);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    }
  }
};

// Format time
const formatTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
};

// Filter section
const filterSection = (
  files: FileMetadata[],
  section: { title: string; filter?: Record<string, any> }
): FileMetadata[] => {
  if (!section.filter) return files;

  return files.filter((file) => {
    if (!file.properties) return false;

    // Check if all filter conditions match
    return Object.entries(section.filter || {}).every(([key, value]) => {
      if (Array.isArray(value)) {
        return value.includes(file.properties?.[key]);
      }
      return file.properties?.[key] === value;
    });
  });
};

// Toggle group expansion
const toggleGroup = (date: string) => {
  if (expandedGroups.value.has(date)) {
    expandedGroups.value.delete(date);
  } else {
    expandedGroups.value.add(date);
  }
};

const isGroupExpanded = (date: string): boolean => {
  return expandedGroups.value.has(date);
};

// Statistics
const totalFiles = computed(() => props.data?.files.length || 0);

const uniqueDates = computed(() => Object.keys(groupedFiles.value).length);

const uniqueTags = computed(() => {
  const tags = new Set<string>();
  props.data?.files.forEach((file) => {
    if (file.properties?.tags) {
      file.properties.tags.forEach((tag: string) => tags.add(tag));
    }
  });
  return tags.size;
});

// Handle file click
const handleFileClick = (file: FileMetadata) => {
  console.log('File clicked:', file);
  // TODO: Open file in editor
};
</script>

<style scoped>
.rollup-group {
  border-left: 2px solid var(--color-border-light);
  padding-left: 1rem;
}
</style>
