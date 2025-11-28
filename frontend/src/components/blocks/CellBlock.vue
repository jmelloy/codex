<script setup lang="ts">
import { ref, computed } from "vue";
import type { Entry } from "@/types";

const props = defineProps<{
  entry: Entry;
  executing?: boolean;
}>();

const emit = defineEmits<{
  (e: "execute"): void;
  (e: "update", data: Partial<Entry>): void;
  (e: "delete"): void;
  (e: "create-variation"): void;
}>();

const isExpanded = ref(true);
const isEditing = ref(false);
const editInputs = ref({ ...props.entry.inputs });
const editInputsJson = ref(JSON.stringify(props.entry.inputs, null, 2));

const entryTypeIcon = computed(() => {
  const icons: Record<string, string> = {
    custom: "📝",
    api_call: "🌐",
    database_query: "🗃️",
    graphql: "◈",
  };
  return icons[props.entry.entry_type] || "📄";
});

const statusClass = computed(() => {
  return {
    created: "status-created",
    running: "status-running",
    completed: "status-completed",
    failed: "status-failed",
  }[props.entry.status] || "";
});

const canExecute = computed(() => props.entry.status === "created");

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
}

function startEditing() {
  editInputs.value = { ...props.entry.inputs };
  editInputsJson.value = JSON.stringify(props.entry.inputs, null, 2);
  isEditing.value = true;
}

function cancelEditing() {
  isEditing.value = false;
  editInputs.value = { ...props.entry.inputs };
  editInputsJson.value = JSON.stringify(props.entry.inputs, null, 2);
}

function saveEditing() {
  try {
    const parsed = JSON.parse(editInputsJson.value);
    emit("update", { inputs: parsed });
    isEditing.value = false;
  } catch (e) {
    alert("Invalid JSON");
  }
}

function formatOutput(outputs: Record<string, unknown>): string {
  return JSON.stringify(outputs, null, 2);
}
</script>

<template>
  <div class="cell-block" :class="[statusClass, { expanded: isExpanded }]">
    <div class="cell-header" @click="toggleExpand">
      <div class="cell-info">
        <span class="cell-icon">{{ entryTypeIcon }}</span>
        <span class="cell-title">{{ entry.title }}</span>
        <span class="cell-id">{{ entry.id.slice(0, 8) }}</span>
      </div>
      <div class="cell-status-row">
        <span class="cell-status" :class="statusClass">{{ entry.status }}</span>
        <span class="cell-expand">{{ isExpanded ? "▼" : "▶" }}</span>
      </div>
    </div>

    <div v-if="isExpanded" class="cell-body">
      <div class="cell-section inputs-section">
        <div class="section-header">
          <h4>Inputs</h4>
          <button
            v-if="!isEditing && entry.status === 'created'"
            class="btn-icon"
            @click.stop="startEditing"
            title="Edit inputs"
          >
            ✏️
          </button>
        </div>

        <div v-if="isEditing" class="edit-form">
          <textarea
            v-model="editInputsJson"
            class="json-editor"
            rows="8"
            placeholder='{"key": "value"}'
          ></textarea>
          <div class="edit-actions">
            <button class="btn btn-secondary" @click="cancelEditing">Cancel</button>
            <button class="btn btn-primary" @click="saveEditing">Save</button>
          </div>
        </div>

        <pre v-else class="code-block">{{ JSON.stringify(entry.inputs, null, 2) }}</pre>
      </div>

      <div v-if="entry.outputs && Object.keys(entry.outputs).length" class="cell-section outputs-section">
        <h4>Outputs</h4>
        <pre class="code-block output-block">{{ formatOutput(entry.outputs) }}</pre>
      </div>

      <div v-if="entry.execution?.error" class="cell-section error-section">
        <h4>Error</h4>
        <pre class="code-block error-block">{{ entry.execution.error }}</pre>
      </div>

      <div v-if="entry.execution?.duration_seconds" class="cell-section meta-section">
        <span class="meta-item">
          ⏱️ {{ entry.execution.duration_seconds.toFixed(2) }}s
        </span>
        <span v-if="entry.execution?.started_at" class="meta-item">
          🕐 {{ new Date(entry.execution.started_at).toLocaleString() }}
        </span>
      </div>

      <div class="cell-actions">
        <button
          v-if="canExecute"
          class="btn btn-primary"
          :disabled="executing"
          @click.stop="emit('execute')"
        >
          {{ executing ? "Running..." : "▶ Run" }}
        </button>
        <button
          class="btn btn-secondary"
          @click.stop="emit('create-variation')"
        >
          📋 Variation
        </button>
        <button
          class="btn btn-danger"
          @click.stop="emit('delete')"
        >
          🗑️ Delete
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cell-block {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.cell-block:hover {
  box-shadow: var(--shadow-sm);
}

.cell-block.status-running {
  border-color: #f59e0b;
}

.cell-block.status-completed {
  border-left: 3px solid #22c55e;
}

.cell-block.status-failed {
  border-left: 3px solid #ef4444;
}

.cell-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--color-background);
  cursor: pointer;
  user-select: none;
}

.cell-header:hover {
  background: var(--color-border);
}

.cell-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cell-icon {
  font-size: 1rem;
}

.cell-title {
  font-weight: 500;
  color: var(--color-text);
}

.cell-id {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  background: var(--color-border);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
}

.cell-status-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.cell-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.status-created {
  background: #e0e7ff;
  color: #4338ca;
}

.status-running {
  background: #fef3c7;
  color: #b45309;
}

.status-completed {
  background: #dcfce7;
  color: #15803d;
}

.status-failed {
  background: #fee2e2;
  color: #b91c1c;
}

.cell-expand {
  font-size: 0.625rem;
  color: var(--color-text-secondary);
}

.cell-body {
  padding: 1rem;
  border-top: 1px solid var(--color-border);
}

.cell-section {
  margin-bottom: 1rem;
}

.cell-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.cell-section h4 {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-secondary);
}

.btn-icon {
  background: none;
  border: none;
  padding: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
  opacity: 0.6;
}

.btn-icon:hover {
  opacity: 1;
}

.code-block {
  background: var(--color-background);
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.output-block {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.error-block {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.meta-section {
  display: flex;
  gap: 1rem;
  padding-top: 0.5rem;
  border-top: 1px dashed var(--color-border);
}

.meta-item {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.cell-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.edit-form {
  margin-bottom: 1rem;
}

.json-editor {
  width: 100%;
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 0.8125rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-background);
  resize: vertical;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-danger {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.btn-danger:hover {
  background: #fecaca;
}
</style>
