<template>
  <div class="custom-block weather-block">
    <div class="block-header">
      <span class="block-icon">{{ weatherIcon }}</span>
      <span class="block-title">Weather</span>
      <button v-if="!loading" class="refresh-btn" @click="fetchWeather" title="Refresh">&#x21bb;</button>
      <button class="edit-btn" @click="$emit('edit')" title="Edit config">&#x270E;</button>
    </div>
    <div class="block-content">
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading weather data...</span>
      </div>

      <div v-else-if="error" class="error">
        <div class="location">{{ config.location || "Unknown Location" }}</div>
        <div class="error-message">{{ error }}</div>
        <button class="retry-btn" @click="fetchWeather">Retry</button>
      </div>

      <div v-else-if="weather" class="weather-data">
        <div class="location">{{ weather.name }}</div>
        <div class="temperature">
          {{ Math.round(weather.main.temp) }}&deg;{{ unitSymbol }}
        </div>
        <div class="description">{{ weather.weather[0]?.description }}</div>
        <div class="details">
          <span>Feels like: {{ Math.round(weather.main.feels_like) }}&deg;{{ unitSymbol }}</span>
          <span>Humidity: {{ weather.main.humidity }}%</span>
        </div>
      </div>

      <div v-else class="not-configured">
        <div class="location">{{ config.location || "Unknown Location" }}</div>
        <div class="block-note">
          <em>Configure the Weather API integration in workspace settings to see live data.</em>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { executeIntegrationEndpoint } from "../../services/integration"

interface WeatherConfig {
  location?: string
  units?: string
  [key: string]: any
}

interface WeatherData {
  name: string
  main: {
    temp: number
    feels_like: number
    humidity: number
  }
  weather: Array<{
    description: string
    icon: string
  }>
}

interface Props {
  config: WeatherConfig
  workspaceId?: string
  notebookId?: string
}

const props = defineProps<Props>()

defineEmits<{
  edit: []
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const weather = ref<WeatherData | null>(null)

const unitSymbol = computed(() => {
  const units = props.config.units || "imperial"
  return units === "metric" ? "C" : units === "kelvin" ? "K" : "F"
})

const weatherIcon = computed(() => {
  if (!weather.value?.weather[0]?.icon) return "\u2600\uFE0F"
  const icon = weather.value.weather[0].icon
  const iconMap: Record<string, string> = {
    "01d": "\u2600\uFE0F",
    "01n": "\uD83C\uDF19",
    "02d": "\u26C5",
    "02n": "\u2601\uFE0F",
    "03d": "\u2601\uFE0F",
    "03n": "\u2601\uFE0F",
    "04d": "\u2601\uFE0F",
    "04n": "\u2601\uFE0F",
    "09d": "\uD83C\uDF27\uFE0F",
    "09n": "\uD83C\uDF27\uFE0F",
    "10d": "\uD83C\uDF26\uFE0F",
    "10n": "\uD83C\uDF27\uFE0F",
    "11d": "\u26C8\uFE0F",
    "11n": "\u26C8\uFE0F",
    "13d": "\uD83C\uDF28\uFE0F",
    "13n": "\uD83C\uDF28\uFE0F",
    "50d": "\uD83C\uDF2B\uFE0F",
    "50n": "\uD83C\uDF2B\uFE0F",
  }
  return iconMap[icon] || "\u2600\uFE0F"
})

async function fetchWeather() {
  if (!props.workspaceId || !props.config.location) {
    return
  }

  loading.value = true
  error.value = null

  try {
    const [city, state, countryRaw] = props.config.location
      .split(",")
      .map((part) => part.trim())

    const country = state && !countryRaw ? "US" : countryRaw

    // Step 1: Geocode the location
    const geoResult = await executeIntegrationEndpoint(
      "weather-api",
      props.workspaceId,
      props.notebookId || "",
      "geocode",
      {
        q: `${city}${state ? "," + state : ""}${country ? "," + country : ""}`,
        limit: 1,
      },
    )

    if (!geoResult.success || !geoResult.data) {
      throw new Error(`Location not found: ${props.config.location}`)
    }

    const geoData = Array.isArray(geoResult.data) ? geoResult.data : geoResult.data.content
    if (!geoData || geoData.length === 0) {
      throw new Error(`Location not found: ${props.config.location}`)
    }

    const { lat, lon } = geoData[0]

    // Step 2: Fetch weather
    const result = await executeIntegrationEndpoint(
      "weather-api",
      props.workspaceId,
      props.notebookId || "",
      "current_weather",
      { lat, lon },
    )

    if (result.success && result.data) {
      weather.value = result.data.name ? result.data : result.data.content || null
    } else {
      throw new Error(result.error || "Failed to fetch weather")
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to fetch weather"
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchWeather()
})
</script>

<style scoped>
.custom-block {
  border: 2px solid var(--color-border-medium, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  padding: var(--spacing-lg, 16px);
  margin: var(--spacing-lg, 16px) 0;
  background: var(--color-bg-secondary, #f9fafb);
}

.weather-block {
  border-color: #fbbf24;
  background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%);
}

.block-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  margin-bottom: var(--spacing-md, 12px);
  font-weight: var(--font-semibold, 600);
  color: var(--color-text-primary, #111827);
}

.block-icon {
  font-size: var(--text-xl, 1.25rem);
}

.block-title {
  font-size: var(--text-lg, 1.125rem);
}

.refresh-btn,
.edit-btn {
  margin-left: auto;
  background: none;
  border: 1px solid var(--color-border-medium, #d1d5db);
  border-radius: var(--radius-sm, 4px);
  padding: 2px 8px;
  cursor: pointer;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.edit-btn {
  margin-left: 4px;
}

.refresh-btn:hover,
.edit-btn:hover {
  background: var(--color-bg-tertiary, #f3f4f6);
}

.block-content {
  color: var(--color-text-primary, #111827);
}

.location {
  font-size: var(--text-lg, 1.125rem);
  font-weight: var(--font-semibold, 600);
  margin-bottom: var(--spacing-xs, 4px);
}

.temperature {
  font-size: 2.5rem;
  font-weight: bold;
  margin: 8px 0;
}

.description {
  text-transform: capitalize;
  font-size: var(--text-base, 1rem);
  margin-bottom: 8px;
}

.details {
  display: flex;
  gap: 16px;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm, 8px);
  padding: var(--spacing-lg, 16px);
  color: var(--color-text-secondary, #6b7280);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border-medium, #e5e7eb);
  border-top-color: #fbbf24;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  color: #dc2626;
  font-size: var(--text-sm, 0.875rem);
  margin-top: 8px;
}

.retry-btn {
  margin-top: 8px;
  padding: 4px 12px;
  background: var(--color-bg-primary, #fff);
  border: 1px solid var(--color-border-medium, #d1d5db);
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  font-size: var(--text-sm, 0.875rem);
}

.block-note {
  margin-top: var(--spacing-md, 12px);
  padding: var(--spacing-sm, 8px);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}
</style>
