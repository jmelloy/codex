<template>
  <Modal :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" title="Create Dynamic View" confirm-text="Create" hide-actions>
    <form @submit.prevent="handleCreate">
      <!-- View Type Selection -->
      <FormGroup label="View Type" v-slot="{ inputId }">
        <select :id="inputId" v-model="selectedType" @change="updateFromTemplate" class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary">
          <option value="">Select a view type...</option>
          <option v-for="type in viewTypes" :key="type.id" :value="type.id">
            {{ type.icon }} {{ type.name }}
          </option>
        </select>
        <p v-if="selectedViewType" class="text-sm text-text-secondary mt-1">
          {{ selectedViewType.description }}
        </p>
      </FormGroup>

      <!-- Show form fields only after a view type is selected -->
      <div v-if="selectedType" class="space-y-4 mt-4">
        <!-- Filename -->
        <FormGroup label="Filename" v-slot="{ inputId }">
          <div class="flex gap-2">
            <input 
              :id="inputId" 
              v-model="filename" 
              placeholder="my-view" 
              required 
              class="flex-1 px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
              @blur="ensureExtension"
            />
            <span class="px-3 py-2 bg-bg-hover rounded-md text-text-secondary">.cdx</span>
          </div>
        </FormGroup>

        <!-- Title -->
        <FormGroup label="View Title" v-slot="{ inputId }">
          <input 
            :id="inputId" 
            v-model="title" 
            placeholder="My Awesome View" 
            required 
            class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
          />
        </FormGroup>

        <!-- Description -->
        <FormGroup label="Description" v-slot="{ inputId }">
          <textarea 
            :id="inputId" 
            v-model="description" 
            placeholder="Describe what this view shows..." 
            rows="2"
            class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary"
          />
        </FormGroup>

        <!-- Query Configuration -->
        <div class="border border-border-light rounded-md p-4 bg-bg-hover">
          <h4 class="text-sm font-semibold text-text-primary mb-3">Query Settings</h4>
          
          <!-- Tags Filter -->
          <FormGroup label="Filter by Tags (comma-separated)" v-slot="{ inputId }">
            <input 
              :id="inputId" 
              v-model="tagsInput" 
              placeholder="task, todo, important" 
              class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary text-sm"
            />
          </FormGroup>

          <!-- Sort Options -->
          <FormGroup label="Sort By" v-slot="{ inputId }" class="mt-3">
            <select :id="inputId" v-model="sortBy" class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary text-sm">
              <option value="created_at desc">Newest First</option>
              <option value="created_at asc">Oldest First</option>
              <option value="modified_at desc">Recently Modified</option>
              <option value="title asc">Title (A-Z)</option>
              <option value="title desc">Title (Z-A)</option>
            </select>
          </FormGroup>
        </div>

        <!-- View-specific Configuration -->
        <div v-if="selectedType === 'kanban'" class="border border-border-light rounded-md p-4 bg-bg-hover">
          <h4 class="text-sm font-semibold text-text-primary mb-3">Kanban Settings</h4>
          <FormGroup label="Status Property" v-slot="{ inputId }">
            <input 
              :id="inputId" 
              v-model="kanbanStatusProperty" 
              placeholder="status" 
              class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary text-sm"
            />
            <p class="text-xs text-text-tertiary mt-1">Property name used to group cards into columns</p>
          </FormGroup>
        </div>

        <div v-if="selectedType === 'gallery'" class="border border-border-light rounded-md p-4 bg-bg-hover">
          <h4 class="text-sm font-semibold text-text-primary mb-3">Gallery Settings</h4>
          <FormGroup label="Columns" v-slot="{ inputId }">
            <input 
              :id="inputId" 
              v-model.number="galleryColumns" 
              type="number" 
              min="2" 
              max="6" 
              class="w-full px-3 py-2 border border-border-medium rounded-md bg-bg-primary text-text-primary text-sm"
            />
          </FormGroup>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-2 justify-end mt-6">
        <button 
          type="button" 
          @click="$emit('update:modelValue', false)"
          class="px-4 py-2 border border-border-medium bg-bg-primary text-text-primary rounded cursor-pointer hover:bg-bg-hover transition"
        >
          Cancel
        </button>
        <button 
          type="submit"
          :disabled="!selectedType || !filename || !title"
          class="px-4 py-2 bg-primary text-white border-none rounded cursor-pointer transition hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Create View
        </button>
      </div>
    </form>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import Modal from './Modal.vue';
import FormGroup from './FormGroup.vue';

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'create', data: { filename: string; content: string }): void;
}>();

// View type definitions
const viewTypes = [
  {
    id: 'kanban',
    name: 'Kanban Board',
    icon: '📋',
    description: 'Organize tasks and items in columns (To Do, In Progress, Done)',
  },
  {
    id: 'task-list',
    name: 'Task List',
    icon: '✅',
    description: 'Simple checklist view with completion status',
  },
  {
    id: 'gallery',
    name: 'Photo Gallery',
    icon: '🖼️',
    description: 'Display images in a responsive grid layout',
  },
  {
    id: 'rollup',
    name: 'Rollup Report',
    icon: '📊',
    description: 'Group and summarize items by date or property',
  },
  {
    id: 'corkboard',
    name: 'Corkboard',
    icon: '📌',
    description: 'Freeform canvas for organizing notes and ideas',
  },
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: '📈',
    description: 'Compose multiple views into a single dashboard',
  },
];

// Form state
const selectedType = ref('');
const filename = ref('');
const title = ref('');
const description = ref('');
const tagsInput = ref('');
const sortBy = ref('created_at desc');

// View-specific options
const kanbanStatusProperty = ref('status');
const galleryColumns = ref(4);

const selectedViewType = computed(() => 
  viewTypes.find(t => t.id === selectedType.value)
);

function ensureExtension() {
  if (filename.value && !filename.value.endsWith('.cdx')) {
    filename.value = filename.value.replace(/\.(md|txt)$/, '') + '.cdx';
  }
}

function updateFromTemplate() {
  // Pre-fill some sensible defaults based on view type
  // Only auto-fill if filename is empty
  if (filename.value === '') {
    switch (selectedType.value) {
      case 'kanban':
        filename.value = 'task-board.cdx';
        title.value = 'Task Board';
        description.value = 'Kanban board for managing tasks';
        tagsInput.value = 'task';
        break;
      case 'task-list':
        filename.value = 'task-list.cdx';
        title.value = 'Task List';
        description.value = 'Simple task list';
        tagsInput.value = 'task';
        break;
      case 'gallery':
        filename.value = 'gallery.cdx';
        title.value = 'Photo Gallery';
        description.value = 'Collection of images';
        tagsInput.value = '';
        break;
      case 'rollup':
        filename.value = 'weekly-rollup.cdx';
        title.value = 'Weekly Rollup';
        description.value = 'Summary of weekly activity';
        break;
      case 'corkboard':
        filename.value = 'corkboard.cdx';
        title.value = 'Corkboard';
        description.value = 'Organize notes and ideas';
        break;
      case 'dashboard':
        filename.value = 'dashboard.cdx';
        title.value = 'Dashboard';
        description.value = 'Composite view of multiple sources';
        break;
    }
  }
}

function generateViewContent(): string {
  const tags = tagsInput.value
    .split(',')
    .map(t => t.trim())
    .filter(Boolean);

  let frontmatter: Record<string, any> = {
    type: 'view',
    view_type: selectedType.value,
    title: title.value,
    description: description.value,
  };

  // Add query if tags are specified
  if (tags.length > 0 || sortBy.value !== 'created_at desc') {
    frontmatter.query = {};
    if (tags.length > 0) {
      frontmatter.query.tags = tags;
    }
    if (sortBy.value && sortBy.value !== 'created_at desc') {
      frontmatter.query.sort = sortBy.value;
    }
  }

  // Add view-specific config
  frontmatter.config = {};

  switch (selectedType.value) {
    case 'kanban':
      frontmatter.config = {
        columns: [
          { id: 'backlog', title: 'Backlog', filter: { [kanbanStatusProperty.value]: 'backlog' } },
          { id: 'todo', title: 'To Do', filter: { [kanbanStatusProperty.value]: 'todo' } },
          { id: 'in-progress', title: 'In Progress', filter: { [kanbanStatusProperty.value]: 'in-progress' } },
          { id: 'done', title: 'Done', filter: { [kanbanStatusProperty.value]: 'done' } },
        ],
        card_fields: ['description', 'priority', 'due_date'],
        drag_drop: true,
        editable: true,
      };
      break;

    case 'task-list':
      frontmatter.config = {
        compact: true,
        show_details: true,
        editable: true,
      };
      break;

    case 'gallery':
      if (!frontmatter.query) {
        frontmatter.query = {};
      }
      frontmatter.query.content_types = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
      frontmatter.config = {
        layout: 'grid',
        columns: galleryColumns.value,
        thumbnail_size: 300,
        show_metadata: true,
        lightbox: true,
      };
      break;

    case 'rollup':
      frontmatter.config = {
        group_by: 'created_at',
        group_format: 'day',
        show_stats: true,
      };
      break;

    case 'corkboard':
      frontmatter.config = {
        layout: 'freeform',
        card_style: 'notecard',
        draggable: true,
        editable: true,
      };
      break;

    case 'dashboard':
      frontmatter.config = {
        layout: [
          {
            type: 'row',
            components: [
              { type: 'mini-view', span: 12, view: 'task-list.cdx' },
            ],
          },
        ],
      };
      break;
  }

  // Convert to YAML format using proper indentation
  const yamlLines = ['---'];
  
  function serializeValue(value: any): string {
    if (typeof value === 'string') {
      // Check if string needs quoting (contains special chars or looks like a number/boolean)
      if (value.match(/^(true|false|null|yes|no|on|off|\d+)$/i) || 
          value.includes(':') || value.includes('#') || value.includes('[') || value.includes('{')) {
        return `"${value.replace(/"/g, '\\"')}"`;
      }
      return value;
    }
    return JSON.stringify(value);
  }
  
  function addToYaml(obj: any, indent = 0) {
    const spaces = '  '.repeat(indent);
    for (const [key, value] of Object.entries(obj)) {
      if (value === null || value === undefined) continue;
      
      if (Array.isArray(value)) {
        if (value.length === 0) {
          yamlLines.push(`${spaces}${key}: []`);
        } else {
          yamlLines.push(`${spaces}${key}:`);
          value.forEach(item => {
            if (typeof item === 'object' && item !== null) {
              yamlLines.push(`${spaces}  - ${JSON.stringify(item)}`);
            } else {
              yamlLines.push(`${spaces}  - ${serializeValue(item)}`);
            }
          });
        }
      } else if (typeof value === 'object' && value !== null) {
        yamlLines.push(`${spaces}${key}:`);
        addToYaml(value, indent + 1);
      } else {
        yamlLines.push(`${spaces}${key}: ${serializeValue(value)}`);
      }
    }
  }
  
  addToYaml(frontmatter);
  yamlLines.push('---');
  yamlLines.push('');
  yamlLines.push(`# ${title.value}`);
  yamlLines.push('');
  if (description.value) {
    yamlLines.push(description.value);
    yamlLines.push('');
  }
  yamlLines.push('This is a dynamic view. Edit the frontmatter above to customize the query and configuration.');
  yamlLines.push('');

  return yamlLines.join('\n');
}

function handleCreate() {
  const content = generateViewContent();
  const finalFilename = filename.value.endsWith('.cdx') 
    ? filename.value 
    : `${filename.value}.cdx`;
  
  emit('create', { filename: finalFilename, content });
  emit('update:modelValue', false);
  
  // Reset form
  selectedType.value = '';
  filename.value = '';
  title.value = '';
  description.value = '';
  tagsInput.value = '';
  sortBy.value = 'created_at desc';
  kanbanStatusProperty.value = 'status';
  galleryColumns.value = 4;
}
</script>

<style scoped>
/* Additional styling if needed */
</style>
