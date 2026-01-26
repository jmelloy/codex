<template>
  <div class="state-renderer">
    <!-- Loading State -->
    <div v-if="loading" class="state-container loading-state">
      <slot name="loading">
        <div class="spinner"></div>
        <p class="state-message">{{ loadingMessage || 'Loading...' }}</p>
      </slot>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="state-container error-state">
      <slot name="error" :error="error">
        <div class="error-icon">⚠️</div>
        <p class="state-message error-message">{{ error }}</p>
        <button v-if="onRetry" @click="onRetry" class="retry-button">
          Retry
        </button>
      </slot>
    </div>

    <!-- Empty State -->
    <div v-else-if="empty" class="state-container empty-state">
      <slot name="empty">
        <div class="empty-icon">📭</div>
        <p class="state-message">{{ emptyMessage || 'No data available' }}</p>
      </slot>
    </div>

    <!-- Content State -->
    <div v-else class="state-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  loading?: boolean
  error?: string | null
  empty?: boolean
  loadingMessage?: string
  emptyMessage?: string
  onRetry?: () => void
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  empty: false
})
</script>

<style scoped>
.state-renderer {
  width: 100%;
  height: 100%;
}

.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
}

.state-message {
  margin: 0.5rem 0;
  color: var(--text-secondary, var(--pen-gray));
  font-size: 0.875rem;
}

/* Loading State */
.loading-state {
  color: var(--text-secondary);
}

.spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid var(--border-light);
  border-top-color: var(--notebook-accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Error State */
.error-state {
  color: var(--pen-red);
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.error-message {
  color: var(--pen-red);
}

.retry-button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  border: 1px solid var(--border-medium);
  border-radius: 0.375rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.retry-button:hover {
  background: var(--bg-hover);
}

/* Empty State */
.empty-state {
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

/* Content State */
.state-content {
  width: 100%;
  height: 100%;
}
</style>
