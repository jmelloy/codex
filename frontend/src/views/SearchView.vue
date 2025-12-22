<script setup lang="ts">
import { ref } from "vue";
import { searchApi } from "@/api";
import type { Entry } from "@/types";

const query = ref("");
const entryType = ref("");
const results = ref<Entry[]>([]);
const loading = ref(false);
const searched = ref(false);

const entryTypes = ["custom", "api_call", "comfyui_workflow", "database_query"];

const search = async () => {
  if (!query.value && !entryType.value) return;

  loading.value = true;
  searched.value = true;

  try {
    const response = await searchApi.search({
      query: query.value || undefined,
      entry_type: entryType.value || undefined,
    });
    results.value = response.results;
  } catch (e) {
    console.error("Search failed:", e);
  } finally {
    loading.value = false;
  }
};

const getStatusClass = (status: string) => {
  return (
    {
      created: "status-created",
      running: "status-running",
      completed: "status-completed",
      failed: "status-failed",
    }[status] || ""
  );
};
</script>

<template>
  <div class="search-view">
    <header class="page-header">
      <h1>Search</h1>
    </header>

    <form class="search-form card" @submit.prevent="search">
      <div class="search-fields">
        <div class="field">
          <label for="query">Search Query</label>
          <input
            id="query"
            v-model="query"
            type="text"
            placeholder="Search entries..."
          />
        </div>
        <div class="field">
          <label for="entryType">Entry Type</label>
          <select id="entryType" v-model="entryType">
            <option value="">All Types</option>
            <option v-for="type in entryTypes" :key="type" :value="type">
              {{ type }}
            </option>
          </select>
        </div>
      </div>
      <button type="submit" class="btn btn-primary" :disabled="loading">
        {{ loading ? "Searching..." : "Search" }}
      </button>
    </form>

    <section class="results-section" v-if="searched">
      <h2>Results ({{ results.length }})</h2>

      <div v-if="results.length === 0" class="empty">
        <p>No entries found matching your search.</p>
      </div>

      <div v-else class="results-list">
        <div v-for="entry in results" :key="entry.id" class="result-card card">
          <div class="result-header">
            <div>
              <span class="entry-type">{{ entry.entry_type }}</span>
              <h3>{{ entry.title }}</h3>
            </div>
            <span class="entry-status" :class="getStatusClass(entry.status)">
              {{ entry.status }}
            </span>
          </div>
          <div class="result-meta">
            <span>ID: {{ entry.id }}</span>
            <span
              >Created: {{ new Date(entry.created_at).toLocaleString() }}</span
            >
          </div>
          <div v-if="entry.metadata?.tags?.length" class="tags">
            <span v-for="tag in entry.metadata.tags" :key="tag" class="tag">{{
              tag
            }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.search-view {
  padding: 2rem;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  font-family: var(--font-handwritten);
  font-size: 2.5rem;
  color: var(--color-primary);
}

.search-form {
  margin-bottom: 2rem;
}

.search-fields {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  font-size: 0.875rem;
}

.field input,
.field select {
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-family: var(--font-body);
  background: var(--color-surface);
  color: var(--color-text);
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(45, 90, 39, 0.1);
}

.results-section h2 {
  margin-bottom: 1rem;
  font-family: var(--font-handwritten);
  color: var(--color-primary);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.result-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateX(4px);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.entry-type {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  letter-spacing: 0.1em;
  font-family: var(--font-mono);
}

.result-header h3 {
  margin-top: 0.25rem;
  font-family: var(--font-handwritten);
  font-size: 1.25rem;
}

.entry-status {
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  font-family: var(--font-mono);
  text-transform: uppercase;
}

.status-created {
  background: #e8f0e3;
  color: var(--color-primary);
}

.status-running {
  background: #fef3cd;
  color: var(--color-warning);
}

.status-completed {
  background: #e8f5e3;
  color: var(--color-success);
}

.status-failed {
  background: #fbe8e8;
  color: var(--color-error);
}

.result-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.empty {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
  font-style: italic;
}
</style>
