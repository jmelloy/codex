<template>
  <div class="integration-settings">
    <div class="settings-header">
      <h2>Integration Plugins</h2>
      <p>Connect Codex to external services and APIs</p>
    </div>

    <div v-if="loading" class="loading-state">
      <p>Loading integrations...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button @click="loadIntegrations">Retry</button>
    </div>

    <div v-else class="integrations-list">
      <div v-if="integrations.length === 0" class="empty-state">
        <p>No integration plugins available.</p>
      </div>

      <div
        v-for="integration in integrations"
        :key="integration.id"
        class="integration-card"
        @click="selectIntegration(integration.id)"
      >
        <div class="integration-header">
          <h3>{{ integration.name }}</h3>
          <span class="version">v{{ integration.version }}</span>
        </div>
        
        <p class="description">{{ integration.description }}</p>
        
        <div class="integration-meta">
          <span class="meta-item">
            <strong>Type:</strong> {{ integration.api_type }}
          </span>
          <span v-if="integration.auth_method" class="meta-item">
            <strong>Auth:</strong> {{ integration.auth_method }}
          </span>
          <span class="meta-item">
            <strong>Author:</strong> {{ integration.author }}
          </span>
        </div>

        <div class="integration-status">
          <span :class="['status-badge', integration.enabled ? 'enabled' : 'disabled']">
            {{ integration.enabled ? 'Enabled' : 'Disabled' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listIntegrations, type Integration } from '../services/integration'

const router = useRouter()

const integrations = ref<Integration[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function loadIntegrations() {
  loading.value = true
  error.value = null
  
  try {
    integrations.value = await listIntegrations()
  } catch (err: any) {
    error.value = err.message || 'Failed to load integrations'
    console.error('Error loading integrations:', err)
  } finally {
    loading.value = false
  }
}

function selectIntegration(integrationId: string) {
  router.push({ name: 'integration-config', params: { integrationId } })
}

onMounted(() => {
  loadIntegrations()
})
</script>

<style scoped>
.integration-settings {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.settings-header {
  margin-bottom: 2rem;
}

.settings-header h2 {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.settings-header p {
  color: #666;
  font-size: 1rem;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
}

.error-state button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.error-state button:hover {
  background: #0056b3;
}

.integrations-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.integration-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.integration-card:hover {
  border-color: #007bff;
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.1);
  transform: translateY(-2px);
}

.integration-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 0.75rem;
}

.integration-header h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
  color: #333;
}

.version {
  font-size: 0.875rem;
  color: #666;
  background: #f0f0f0;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.description {
  color: #555;
  line-height: 1.5;
  margin-bottom: 1rem;
  min-height: 3rem;
}

.integration-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.meta-item {
  color: #666;
}

.meta-item strong {
  color: #333;
}

.integration-status {
  display: flex;
  justify-content: flex-end;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.enabled {
  background: #d4edda;
  color: #155724;
}

.status-badge.disabled {
  background: #f8d7da;
  color: #721c24;
}
</style>
