<template>
  <div class="custom-block weather-block">
    <div class="block-header">
      <span class="block-icon">☀️</span>
      <span class="block-title">Weather</span>
    </div>
    <div class="block-content">
      <div class="location">{{ config.location || "Unknown Location" }}</div>
      <div class="units" v-if="config.units">Units: {{ config.units }}</div>
      <div class="block-note">
        <em
          >Note: This is a placeholder. Enable the Weather API integration to
          see live data.</em
        >
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface WeatherConfig {
  location?: string;
  units?: string;
  [key: string]: any;
}

interface Props {
  config: WeatherConfig;
}

defineProps<Props>();
</script>

<style scoped>
.custom-block {
  border: 2px solid var(--color-border-medium);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin: var(--spacing-lg) 0;
  background: var(--color-bg-secondary);
}

.weather-block {
  border-color: #fbbf24;
  background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%);
}

.block-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.block-icon {
  font-size: var(--text-xl);
}

.block-title {
  font-size: var(--text-lg);
}

.block-content {
  color: var(--color-text-primary);
}

.location {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--spacing-xs);
}

.units {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
}

.block-note {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
</style>
