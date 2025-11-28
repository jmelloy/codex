<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { pagesApi, entriesApi } from "@/api";
import type { Page } from "@/types";
import DatabaseQueryForm from "@/components/entry/DatabaseQueryForm.vue";
import GraphQLForm from "@/components/entry/GraphQLForm.vue";
import ApiCallForm from "@/components/entry/ApiCallForm.vue";
import CustomForm from "@/components/entry/CustomForm.vue";
import TextForm from "@/components/entry/TextForm.vue";

const route = useRoute();
const router = useRouter();
const notebooksStore = useNotebooksStore();

const page = ref<Page | null>(null);
const loading = ref(true);
const submitting = ref(false);
const error = ref("");

const notebookId = computed(() => route.params.notebookId as string);
const pageId = computed(() => route.params.pageId as string);
const notebook = computed(() => notebooksStore.notebooks.get(notebookId.value));

// Entry form data - default to text for Notion-like experience
const entryType = ref(route.query.type as string || "text");
const title = ref("");
const inputs = ref<Record<string, unknown>>({});
const tags = ref("");

const entryTypes = [
  {
    value: "text",
    label: "Text",
    description: "Plain text or markdown content",
    icon: "📝",
  },
  {
    value: "custom",
    label: "Custom",
    description: "Custom entry with JSON data",
    icon: "🔧",
  },
  {
    value: "api_call",
    label: "API Call",
    description: "HTTP API request tracking",
    icon: "🌐",
  },
  {
    value: "database_query",
    label: "SQL Query",
    description: "Execute SQL queries against databases",
    icon: "🗃️",
  },
  {
    value: "graphql",
    label: "GraphQL",
    description: "GraphQL API queries and mutations",
    icon: "◈",
  },
];

const currentEntryType = computed(() =>
  entryTypes.find((t) => t.value === entryType.value),
);

const formComponent = computed(() => {
  switch (entryType.value) {
    case "text":
      return TextForm;
    case "database_query":
      return DatabaseQueryForm;
    case "graphql":
      return GraphQLForm;
    case "api_call":
      return ApiCallForm;
    case "custom":
    default:
      return CustomForm;
  }
});

// Reset inputs when entry type changes
watch(entryType, () => {
  inputs.value = {};
});

onMounted(async () => {
  await notebooksStore.loadNotebook(notebookId.value);
  try {
    page.value = await pagesApi.get(notebooksStore.workspacePath, pageId.value);
  } catch (e) {
    console.error("Failed to load page:", e);
    error.value = "Failed to load page";
  } finally {
    loading.value = false;
  }
});

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
  if (!title.value.trim()) return false;

  // Validate based on entry type
  switch (entryType.value) {
    case "database_query":
      return !!(inputs.value.connection_string && inputs.value.query);
    case "graphql":
      return !!(inputs.value.url && inputs.value.query);
    case "api_call":
      return !!inputs.value.url;
    case "text":
    case "custom":
    default:
      return true;
  }
});

const submitEntry = async () => {
  if (!isValid.value) return;

  submitting.value = true;
  error.value = "";

  try {
    await entriesApi.create(notebooksStore.workspacePath, pageId.value, {
      entry_type: entryType.value,
      title: title.value,
      inputs: inputs.value,
      tags: parseTags(tags.value),
    });

    // Navigate back to page detail
    router.push(`/notebooks/${notebookId.value}/pages/${pageId.value}`);
  } catch (e) {
    console.error("Failed to create entry:", e);
    error.value = e instanceof Error ? e.message : "Failed to create entry";
  } finally {
    submitting.value = false;
  }
};

const cancel = () => {
  router.push(`/notebooks/${notebookId.value}/pages/${pageId.value}`);
};
</script>

<template>
  <div class="create-entry-view" v-if="page">
    <header class="page-header">
      <div class="breadcrumb">
        <RouterLink to="/notebooks">Notebooks</RouterLink>
        <span>/</span>
        <RouterLink :to="`/notebooks/${notebookId}`">{{
          notebook?.title
        }}</RouterLink>
        <span>/</span>
        <RouterLink :to="`/notebooks/${notebookId}/pages/${pageId}`">{{
          page.title
        }}</RouterLink>
        <span>/</span>
        <span>New Entry</span>
      </div>

      <h1>Create New Entry</h1>
    </header>

    <form class="entry-form card" @submit.prevent="submitEntry">
      <!-- Entry Type Selection -->
      <section class="form-section">
        <h2>Entry Type</h2>
        <div class="entry-type-grid">
          <button
            v-for="type in entryTypes"
            :key="type.value"
            type="button"
            class="type-card"
            :class="{ selected: entryType === type.value }"
            @click="entryType = type.value"
          >
            <span class="type-icon">{{ type.icon }}</span>
            <span class="type-label">{{ type.label }}</span>
            <span class="type-description">{{ type.description }}</span>
          </button>
        </div>
      </section>

      <!-- Basic Info -->
      <section class="form-section">
        <h2>Basic Information</h2>
        <div class="form-group">
          <label for="title">Title <span class="required">*</span></label>
          <input
            id="title"
            v-model="title"
            type="text"
            placeholder="Enter a descriptive title for this entry"
            required
          />
        </div>

        <div class="form-group">
          <label for="tags">Tags</label>
          <input
            id="tags"
            v-model="tags"
            type="text"
            placeholder="tag1, tag2, tag3"
          />
          <span class="hint">Comma-separated list of tags</span>
        </div>
      </section>

      <!-- Dynamic Form based on Entry Type -->
      <section class="form-section">
        <h2>{{ currentEntryType?.label }} Configuration</h2>
        <component
          :is="formComponent"
          :model-value="inputs"
          @update:model-value="handleInputsUpdate"
        />
      </section>

      <!-- Error Display -->
      <div v-if="error" class="error-banner">
        {{ error }}
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" @click="cancel">
          Cancel
        </button>
        <button
          type="submit"
          class="btn btn-primary"
          :disabled="!isValid || submitting"
        >
          {{ submitting ? "Creating..." : "Create Entry" }}
        </button>
      </div>
    </form>
  </div>

  <div v-else-if="loading" class="loading">Loading...</div>
  <div v-else-if="error" class="error">{{ error }}</div>
</template>

<style scoped>
.page-header {
  margin-bottom: 2rem;
}

.breadcrumb {
  display: flex;
  gap: 0.5rem;
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.breadcrumb a {
  color: var(--color-text-secondary);
}

.breadcrumb a:hover {
  color: var(--color-primary);
}

.entry-form {
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
}

.entry-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.25rem;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.type-card:hover {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.02);
}

.type-card.selected {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.05);
}

.type-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.type-label {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.type-description {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
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

.form-group input {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.hint {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.error-banner {
  padding: 1rem;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: var(--radius-md);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}

.loading,
.error {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}
</style>
