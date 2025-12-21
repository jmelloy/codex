<script setup lang="ts">
import { computed } from "vue";

interface RenderedField {
  key: string;
  type: string;
  value: any;
  display: string;
}

interface Props {
  rendered: Record<string, RenderedField>;
}

const props = defineProps<Props>();

// Group fields for better display
const commonFields = ["title", "date", "author", "created_at", "updated_at"];
const otherFields = computed(() => {
  return Object.keys(props.rendered).filter((key) => !commonFields.includes(key));
});
</script>

<template>
  <div class="frontmatter-viewer">
    <div class="frontmatter-grid">
      <!-- Display common fields in prominent positions -->
      <div
        v-for="key in commonFields"
        :key="key"
        v-show="rendered[key]"
        class="field"
        :class="`field-${rendered[key]?.type || 'text'}`"
      >
        <label class="field-label">{{ key }}</label>
        <div class="field-value">
          <!-- Text -->
          <span v-if="rendered[key]?.type === 'text'" class="value-text">
            {{ rendered[key].display }}
          </span>

          <!-- Date -->
          <span v-else-if="rendered[key]?.type === 'date'" class="value-date">
            {{ rendered[key].display }}
          </span>

          <!-- Number -->
          <span v-else-if="rendered[key]?.type === 'number'" class="value-number">
            {{ rendered[key].display }}
          </span>

          <!-- Boolean -->
          <span v-else-if="rendered[key]?.type === 'boolean'" class="value-boolean">
            <span
              class="boolean-indicator"
              :class="{ active: rendered[key].value }"
            >
              {{ rendered[key].display }}
            </span>
          </span>

          <!-- List/Tags -->
          <div v-else-if="rendered[key]?.type === 'list'" class="value-list">
            <span
              v-for="(item, index) in rendered[key].value"
              :key="index"
              class="list-item"
            >
              {{ item }}
            </span>
          </div>

          <!-- Link -->
          <a
            v-else-if="rendered[key]?.type === 'link'"
            :href="rendered[key].value"
            target="_blank"
            rel="noopener noreferrer"
            class="value-link"
          >
            {{ rendered[key].display }}
          </a>

          <!-- Markdown (render as text for now, can be enhanced) -->
          <div v-else-if="rendered[key]?.type === 'markdown'" class="value-markdown">
            {{ rendered[key].display }}
          </div>

          <!-- Fallback for unknown types -->
          <span v-else class="value-default">
            {{ rendered[key]?.display || rendered[key]?.value }}
          </span>
        </div>
      </div>

      <!-- Display other fields -->
      <div
        v-for="key in otherFields"
        :key="key"
        class="field"
        :class="`field-${rendered[key]?.type || 'text'}`"
      >
        <label class="field-label">{{ key }}</label>
        <div class="field-value">
          <!-- Text, Date, Number, Boolean, List, Link, Markdown - Same as above -->
          <span v-if="rendered[key]?.type === 'text'" class="value-text">
            {{ rendered[key].display }}
          </span>
          <span v-else-if="rendered[key]?.type === 'date'" class="value-date">
            {{ rendered[key].display }}
          </span>
          <span v-else-if="rendered[key]?.type === 'number'" class="value-number">
            {{ rendered[key].display }}
          </span>
          <span v-else-if="rendered[key]?.type === 'boolean'" class="value-boolean">
            <span class="boolean-indicator" :class="{ active: rendered[key].value }">
              {{ rendered[key].display }}
            </span>
          </span>
          <div v-else-if="rendered[key]?.type === 'list'" class="value-list">
            <span v-for="(item, index) in rendered[key].value" :key="index" class="list-item">
              {{ item }}
            </span>
          </div>
          <a
            v-else-if="rendered[key]?.type === 'link'"
            :href="rendered[key].value"
            target="_blank"
            rel="noopener noreferrer"
            class="value-link"
          >
            {{ rendered[key].display }}
          </a>
          <div v-else-if="rendered[key]?.type === 'markdown'" class="value-markdown">
            {{ rendered[key].display }}
          </div>
          <span v-else class="value-default">
            {{ rendered[key]?.display || rendered[key]?.value }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.frontmatter-viewer {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.frontmatter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-secondary);
}

.field-value {
  font-size: 0.875rem;
  color: var(--color-text);
}

.value-text {
  font-weight: 500;
}

.value-date {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}

.value-number {
  font-family: var(--font-mono);
  font-weight: 600;
}

.value-boolean {
  display: inline-block;
}

.boolean-indicator {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  background: var(--color-border);
  color: var(--color-text-secondary);
}

.boolean-indicator.active {
  background: #10b981;
  color: white;
}

.value-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.list-item {
  display: inline-block;
  padding: 0.125rem 0.625rem;
  background: var(--color-border);
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text);
}

.value-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.value-link:hover {
  text-decoration: underline;
}

.value-markdown {
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.value-default {
  font-style: italic;
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .frontmatter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
