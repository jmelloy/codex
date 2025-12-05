<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { entriesApi, pagesApi, notebooksApi } from "@/api";
import ComfyUIForm from "@/components/entry/ComfyUIForm.vue";

const router = useRouter();
const notebooksStore = useNotebooksStore();

// Form state
const title = ref("");
const inputs = ref<Record<string, unknown>>({});
const tags = ref("");
const submitting = ref(false);
const error = ref("");
const successMessage = ref("");

// Notebook/Page selection
const selectedNotebook = ref("");
const selectedPage = ref("");
const notebooks = ref<any[]>([]);
const pages = ref<any[]>([]);
const loadingNotebooks = ref(false);
const loadingPages = ref(false);

// Create new notebook/page
const showCreateNotebook = ref(false);
const showCreatePage = ref(false);
const newNotebookTitle = ref("");
const newNotebookDescription = ref("");
const newPageTitle = ref("");

const handleInputsUpdate = (newInputs: Record<string, unknown>) => {
  inputs.value = newInputs;
};

const parseTags = (tagsString: string): string[] => {
  return tagsString
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
};

const isValid = computed(() => {
  return !!(
    title.value.trim() &&
    inputs.value.workflow &&
    selectedNotebook.value &&
    selectedPage.value
  );
});

// Load notebooks on mount
const loadNotebooks = async () => {
  loadingNotebooks.value = true;
  try {
    const response = await notebooksApi.list(notebooksStore.workspacePath);
    notebooks.value = response;
    if (response.length > 0 && !selectedNotebook.value) {
      selectedNotebook.value = response[0].id;
      await loadPages();
    }
  } catch (e) {
    console.error("Failed to load notebooks:", e);
    error.value = "Failed to load notebooks";
  } finally {
    loadingNotebooks.value = false;
  }
};

// Load pages when notebook changes
const loadPages = async () => {
  if (!selectedNotebook.value) return;

  loadingPages.value = true;
  try {
    const response = await pagesApi.list(
      notebooksStore.workspacePath,
      selectedNotebook.value,
    );
    pages.value = response;
    if (response.length > 0) {
      selectedPage.value = response[0].id;
    } else {
      selectedPage.value = "";
    }
  } catch (e) {
    console.error("Failed to load pages:", e);
    error.value = "Failed to load pages";
  } finally {
    loadingPages.value = false;
  }
};

const createNotebook = async () => {
  if (!newNotebookTitle.value.trim()) return;

  try {
    const notebook = await notebooksApi.create(notebooksStore.workspacePath, {
      title: newNotebookTitle.value,
      description: newNotebookDescription.value,
    });
    notebooks.value.push(notebook);
    selectedNotebook.value = notebook.id;
    showCreateNotebook.value = false;
    newNotebookTitle.value = "";
    newNotebookDescription.value = "";
    await loadPages();
  } catch (e) {
    console.error("Failed to create notebook:", e);
    error.value = "Failed to create notebook";
  }
};

const createPage = async () => {
  if (!newPageTitle.value.trim() || !selectedNotebook.value) return;

  try {
    const page = await pagesApi.create(
      notebooksStore.workspacePath,
      selectedNotebook.value,
      {
        title: newPageTitle.value,
      },
    );
    pages.value.push(page);
    selectedPage.value = page.id;
    showCreatePage.value = false;
    newPageTitle.value = "";
  } catch (e) {
    console.error("Failed to create page:", e);
    error.value = "Failed to create page";
  }
};

const submitWorkflow = async () => {
  if (!isValid.value) return;

  submitting.value = true;
  error.value = "";
  successMessage.value = "";

  try {
    await entriesApi.create(
      notebooksStore.workspacePath,
      selectedPage.value,
      {
        entry_type: "comfyui",
        title: title.value,
        inputs: inputs.value,
        tags: parseTags(tags.value),
      },
    );

    successMessage.value = "ComfyUI workflow entry created successfully!";
    
    // Navigate to the entry's page after a delay
    setTimeout(() => {
      router.push(
        `/notebooks/${selectedNotebook.value}/pages/${selectedPage.value}`,
      );
    }, 1500);
  } catch (e) {
    console.error("Failed to create entry:", e);
    error.value = e instanceof Error ? e.message : "Failed to create workflow entry";
  } finally {
    submitting.value = false;
  }
};

const reset = () => {
  title.value = "";
  inputs.value = {};
  tags.value = "";
  error.value = "";
  successMessage.value = "";
};

// Load notebooks on component mount
loadNotebooks();
</script>

<template>
  <div class="comfyui-view">
    <header class="page-header">
      <div class="header-content">
        <div>
          <h1>🎨 ComfyUI Integration</h1>
          <p class="subtitle">
            Execute ComfyUI workflows and track generated images
          </p>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary" @click="reset">Reset Form</button>
        </div>
      </div>
    </header>

    <div class="comfyui-content">
      <aside class="info-sidebar">
        <div class="info-card">
          <h3>📋 About ComfyUI Integration</h3>
          <p>
            This page allows you to execute ComfyUI workflows and automatically
            track the generated images and outputs in your laboratory journal.
          </p>
        </div>

        <div class="info-card">
          <h3>🚀 Quick Start</h3>
          <ol>
            <li>Make sure ComfyUI is running (default: http://127.0.0.1:8188)</li>
            <li>Select or create a notebook and page</li>
            <li>Paste your workflow JSON</li>
            <li>Give it a descriptive title</li>
            <li>Click "Create Workflow Entry"</li>
          </ol>
        </div>

        <div class="info-card">
          <h3>💡 Tips</h3>
          <ul>
            <li>Export workflows using "Save (API Format)" in ComfyUI</li>
            <li>Use tags to organize different types of generations</li>
            <li>All generated images are automatically saved</li>
            <li>Execution progress is tracked in real-time</li>
          </ul>
        </div>
      </aside>

      <main class="workflow-form-container">
        <form class="workflow-form card" @submit.prevent="submitWorkflow">
          <!-- Notebook and Page Selection -->
          <section class="form-section">
            <h2>Target Location</h2>
            
            <div class="form-group">
              <label for="notebook">Notebook</label>
              <div class="select-with-action">
                <select
                  id="notebook"
                  v-model="selectedNotebook"
                  @change="loadPages"
                  :disabled="loadingNotebooks"
                >
                  <option value="">Select a notebook...</option>
                  <option
                    v-for="notebook in notebooks"
                    :key="notebook.id"
                    :value="notebook.id"
                  >
                    {{ notebook.title }}
                  </option>
                </select>
                <button
                  type="button"
                  class="btn-icon"
                  @click="showCreateNotebook = !showCreateNotebook"
                  title="Create new notebook"
                >
                  ➕
                </button>
              </div>
            </div>

            <div v-if="showCreateNotebook" class="create-form">
              <input
                v-model="newNotebookTitle"
                type="text"
                placeholder="New notebook title"
              />
              <input
                v-model="newNotebookDescription"
                type="text"
                placeholder="Description (optional)"
              />
              <div class="form-actions-inline">
                <button
                  type="button"
                  class="btn btn-sm btn-primary"
                  @click="createNotebook"
                >
                  Create
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-secondary"
                  @click="showCreateNotebook = false"
                >
                  Cancel
                </button>
              </div>
            </div>

            <div class="form-group">
              <label for="page">Page</label>
              <div class="select-with-action">
                <select
                  id="page"
                  v-model="selectedPage"
                  :disabled="!selectedNotebook || loadingPages"
                >
                  <option value="">Select a page...</option>
                  <option
                    v-for="page in pages"
                    :key="page.id"
                    :value="page.id"
                  >
                    {{ page.title }}
                  </option>
                </select>
                <button
                  type="button"
                  class="btn-icon"
                  :disabled="!selectedNotebook"
                  @click="showCreatePage = !showCreatePage"
                  title="Create new page"
                >
                  ➕
                </button>
              </div>
            </div>

            <div v-if="showCreatePage" class="create-form">
              <input
                v-model="newPageTitle"
                type="text"
                placeholder="New page title"
              />
              <div class="form-actions-inline">
                <button
                  type="button"
                  class="btn btn-sm btn-primary"
                  @click="createPage"
                >
                  Create
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-secondary"
                  @click="showCreatePage = false"
                >
                  Cancel
                </button>
              </div>
            </div>
          </section>

          <!-- Basic Info -->
          <section class="form-section">
            <h2>Entry Information</h2>
            
            <div class="form-group">
              <label for="title">
                Title <span class="required">*</span>
              </label>
              <input
                id="title"
                v-model="title"
                type="text"
                placeholder="e.g., 'Sunset landscape with mountains'"
                required
              />
            </div>

            <div class="form-group">
              <label for="tags">Tags</label>
              <input
                id="tags"
                v-model="tags"
                type="text"
                placeholder="landscape, sunset, sdxl"
              />
              <span class="hint">Comma-separated list of tags</span>
            </div>
          </section>

          <!-- ComfyUI Configuration -->
          <section class="form-section">
            <h2>ComfyUI Workflow Configuration</h2>
            <ComfyUIForm
              :model-value="inputs"
              @update:model-value="handleInputsUpdate"
            />
          </section>

          <!-- Success/Error Messages -->
          <div v-if="successMessage" class="success-banner">
            ✓ {{ successMessage }}
          </div>
          <div v-if="error" class="error-banner">
            ✕ {{ error }}
          </div>

          <!-- Actions -->
          <div class="form-actions">
            <button
              type="button"
              class="btn btn-secondary"
              @click="reset"
              :disabled="submitting"
            >
              Reset
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="!isValid || submitting"
            >
              {{ submitting ? "Creating..." : "Create Workflow Entry" }}
            </button>
          </div>
        </form>
      </main>
    </div>
  </div>
</template>

<style scoped>
.comfyui-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.subtitle {
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.comfyui-content {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 2rem;
  align-items: start;
}

.info-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: sticky;
  top: 2rem;
}

.info-card {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.5rem;
}

.info-card h3 {
  font-size: 1rem;
  margin-bottom: 0.75rem;
  color: var(--color-text);
}

.info-card p {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.info-card ol,
.info-card ul {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
  padding-left: 1.25rem;
}

.info-card li {
  margin: 0.5rem 0;
}

.workflow-form-container {
  flex: 1;
}

.workflow-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-section h2 {
  font-size: 1.125rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  margin: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  font-size: 0.875rem;
}

.required {
  color: #dc2626;
}

.form-group input,
.form-group select {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  background: white;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-group input:disabled,
.form-group select:disabled {
  background: var(--color-bg-secondary);
  cursor: not-allowed;
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.select-with-action {
  display: flex;
  gap: 0.5rem;
}

.select-with-action select {
  flex: 1;
}

.btn-icon {
  width: 40px;
  height: 40px;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: white;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover:not(:disabled) {
  background: var(--color-bg-secondary);
  border-color: var(--color-primary);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.create-form input {
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.form-actions-inline {
  display: flex;
  gap: 0.5rem;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.success-banner {
  padding: 1rem;
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error-banner {
  padding: 1rem;
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

@media (max-width: 1024px) {
  .comfyui-content {
    grid-template-columns: 1fr;
  }

  .info-sidebar {
    position: static;
  }
}
</style>
