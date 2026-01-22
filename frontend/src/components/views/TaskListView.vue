<template>
  <div class="task-list-view" :class="{ 'compact': config.compact }">
    <!-- Header -->
    <div v-if="!config.compact" class="mb-4">
      <h2 class="text-xl font-semibold text-gray-800">{{ definition?.title }}</h2>
      <p v-if="definition?.description" class="text-sm text-gray-600 mt-1">
        {{ definition.description }}
      </p>
    </div>

    <!-- Tasks -->
    <div class="space-y-2">
      <div
        v-for="task in displayedTasks"
        :key="task.id"
        class="task-item bg-white rounded-lg border border-gray-200 p-3 hover:shadow-md transition cursor-pointer"
        :class="getTaskStatusClass(task)"
        @click="handleTaskClick(task)"
      >
        <!-- Checkbox and Title -->
        <div class="flex items-start gap-3">
          <input
            v-if="config.editable !== false"
            type="checkbox"
            :checked="isTaskCompleted(task)"
            class="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            @change.stop="toggleTaskStatus(task)"
          />

          <div class="flex-1 min-w-0">
            <div class="font-medium text-gray-900" :class="{ 'line-through text-gray-500': isTaskCompleted(task) }">
              {{ task.title || task.filename }}
            </div>

            <!-- Details -->
            <div v-if="config.show_details !== false" class="mt-1 space-y-1">
              <div v-if="task.description" class="text-sm text-gray-600">
                {{ truncateText(task.description, 100) }}
              </div>

              <div class="flex flex-wrap gap-2 text-xs">
                <!-- Priority -->
                <span
                  v-if="task.properties?.priority"
                  class="px-2 py-1 rounded"
                  :class="getPriorityClass(task.properties.priority)"
                >
                  {{ task.properties.priority }}
                </span>

                <!-- Due Date -->
                <span
                  v-if="task.properties?.due_date"
                  class="px-2 py-1 bg-gray-100 text-gray-700 rounded"
                  :class="{ 'bg-red-100 text-red-700': isOverdue(task) }"
                >
                  📅 {{ formatDate(task.properties.due_date) }}
                </span>

                <!-- Tags -->
                <span
                  v-for="tag in task.properties?.tags"
                  :key="tag"
                  class="px-2 py-1 bg-blue-100 text-blue-700 rounded"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="displayedTasks.length === 0" class="text-center py-8 text-gray-400">
        <div class="text-4xl mb-2">✓</div>
        <div class="text-sm">No tasks found</div>
      </div>

      <!-- Show More -->
      <div v-if="hasMoreTasks" class="text-center pt-2">
        <button
          class="text-sm text-blue-600 hover:text-blue-700 font-medium"
          @click="showAll = true"
        >
          Show {{ remainingTasksCount }} more
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { TaskListConfig, ViewDefinition } from '@/services/viewParser';
import type { QueryResult } from '@/services/queryService';
import type { FileMetadata } from '@/services/codex';

const props = defineProps<{
  data: QueryResult | null;
  config: TaskListConfig;
  definition?: ViewDefinition;
  workspaceId: number;
}>();

const emit = defineEmits<{
  (e: 'update', event: { fileId: number; updates: Record<string, any> }): void;
  (e: 'refresh'): void;
}>();

const showAll = ref(false);

// Get all tasks
const allTasks = computed(() => props.data?.files || []);

// Get displayed tasks (respecting max_items if in compact mode)
const displayedTasks = computed(() => {
  const max = props.config.max_items;
  if (max && !showAll.value) {
    return allTasks.value.slice(0, max);
  }
  return allTasks.value;
});

const hasMoreTasks = computed(() => {
  const max = props.config.max_items;
  return max && !showAll.value && allTasks.value.length > max;
});

const remainingTasksCount = computed(() => {
  const max = props.config.max_items || 0;
  return allTasks.value.length - max;
});

// Check if task is completed
const isTaskCompleted = (task: FileMetadata): boolean => {
  const status = task.properties?.status;
  return status === 'done' || status === 'completed';
};

// Check if task is overdue
const isOverdue = (task: FileMetadata): boolean => {
  if (!task.properties?.due_date) return false;
  const dueDate = new Date(task.properties.due_date);
  return dueDate < new Date() && !isTaskCompleted(task);
};

// Get task status class
const getTaskStatusClass = (task: FileMetadata): string => {
  if (isTaskCompleted(task)) return 'opacity-60';
  if (isOverdue(task)) return 'border-red-300 bg-red-50';
  return '';
};

// Get priority class
const getPriorityClass = (priority: string): string => {
  const classes: Record<string, string> = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700',
  };
  return classes[priority?.toLowerCase()] || 'bg-gray-100 text-gray-700';
};

// Toggle task status
const toggleTaskStatus = (task: FileMetadata) => {
  const currentStatus = task.properties?.status;
  const newStatus = currentStatus === 'done' ? 'todo' : 'done';

  emit('update', {
    fileId: task.id,
    updates: { status: newStatus },
  });
};

// Handle task click
const handleTaskClick = (task: FileMetadata) => {
  console.log('Task clicked:', task);
  // TODO: Open task in editor or modal
};

// Format date
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  } else if (date.toDateString() === tomorrow.toDateString()) {
    return 'Tomorrow';
  } else {
    return date.toLocaleDateString();
  }
};

// Truncate text
const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};
</script>

<style scoped>
.task-list-view.compact {
  font-size: 0.875rem;
}

.task-item {
  transition: all 0.2s;
}

.task-item:hover {
  transform: translateX(4px);
}
</style>
