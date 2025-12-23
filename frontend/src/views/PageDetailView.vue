<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useNotebooksStore } from "@/stores/notebooks";
import { pagesApi } from "@/api";
import type { Page } from "@/types";

const route = useRoute();
const notebooksStore = useNotebooksStore();

const page = ref<Page | null>(null);
const loading = ref(true);

const notebookId = computed(() => route.params.notebookId as string);
const pageId = computed(() => route.params.pageId as string);

onMounted(async () => {
  await loadPage();
});

watch([notebookId, pageId], async () => {
  await loadPage();
});

async function loadPage() {
  loading.value = true;
  await notebooksStore.loadNotebook(notebookId.value);
  try {
    page.value = await pagesApi.get(pageId.value);
  } catch (e) {
    console.error("Failed to load page:", e);
  } finally {
    loading.value = false;
  }
}

async function updateNarrative(field: string, content: string) {
  if (!page.value) return;
  try {
    const updatedNarrative = { ...page.value.narrative, [field]: content };
    await pagesApi.update(pageId.value, {
      narrative: updatedNarrative,
    });
    page.value.narrative = updatedNarrative;
  } catch (e) {
    console.error("Failed to update narrative:", e);
  }
}

const formattedDate = computed(() => {
  if (!page.value?.date) return null;
  return new Date(page.value.date).toLocaleDateString();
});
</script>

<template>
  <div class="page-detail-view">
    <div v-if="loading" class="loading">Loading page...</div>

    <div v-else-if="page" class="page-content">
      <div class="page-header">
        <h1 class="page-title">{{ page.title }}</h1>
        <p v-if="formattedDate" class="page-date">{{ formattedDate }}</p>
      </div>

      <div class="narrative-section">
        <h2>Narrative</h2>
        
        <div class="narrative-field">
          <h3>Goals</h3>
          <textarea
            :value="page.narrative?.goals || ''"
            @input="updateNarrative('goals', ($event.target as HTMLTextAreaElement).value)"
            placeholder="What are you trying to achieve?"
            rows="3"
          ></textarea>
        </div>

        <div class="narrative-field">
          <h3>Hypothesis</h3>
          <textarea
            :value="page.narrative?.hypothesis || ''"
            @input="updateNarrative('hypothesis', ($event.target as HTMLTextAreaElement).value)"
            placeholder="What do you expect to happen?"
            rows="3"
          ></textarea>
        </div>

        <div class="narrative-field">
          <h3>Observations</h3>
          <textarea
            :value="page.narrative?.observations || ''"
            @input="updateNarrative('observations', ($event.target as HTMLTextAreaElement).value)"
            placeholder="What did you observe?"
            rows="4"
          ></textarea>
        </div>

        <div class="narrative-field">
          <h3>Conclusions</h3>
          <textarea
            :value="page.narrative?.conclusions || ''"
            @input="updateNarrative('conclusions', ($event.target as HTMLTextAreaElement).value)"
            placeholder="What did you learn?"
            rows="4"
          ></textarea>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-detail-view {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-secondary);
}

.page-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.page-date {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.narrative-section {
  margin-bottom: 2rem;
}

.narrative-section h2 {
  font-size: 1.25rem;
  margin-bottom: 1rem;
}

.narrative-field {
  margin-bottom: 1.5rem;
}

.narrative-field h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.narrative-field textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: inherit;
  font-size: 0.875rem;
  resize: vertical;
}

.narrative-field textarea:focus {
  outline: none;
  border-color: var(--color-primary, #4f46e5);
}
</style>
