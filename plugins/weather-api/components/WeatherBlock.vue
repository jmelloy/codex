<template>
  <div class="custom-block weather-block">
    <div class="block-header">
      <span class="block-icon">{{ weatherIcon }}</span>
      <span class="block-title">Weather</span>
    </div>
    <div class="block-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>Loading weather data...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error">
        <div class="location">{{ config.location || "Unknown Location" }}</div>
        <div class="error-message">{{ error }}</div>
      </div>

      <!-- Weather data -->
      <div v-else-if="weather" class="weather-data">
        <div class="location">{{ weather.name }}</div>
        <div class="temperature">
          {{ Math.round(weather.main.temp) }}°{{ unitSymbol }}
        </div>
        <div class="description">{{ weather.weather[0]?.description }}</div>
        <div class="details">
          <span
            >Feels like: {{ Math.round(weather.main.feels_like) }}°{{
              unitSymbol
            }}</span
          >
          <span>Humidity: {{ weather.main.humidity }}%</span>
        </div>
      </div>

      <!-- Not configured -->
      <div v-else class="not-configured">
        <div class="location">{{ config.location || "Unknown Location" }}</div>
        <div class="block-note">
          <em
            >Configure the Weather API integration in workspace settings to see
            live data.</em
          >
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";

interface WeatherConfig {
  location?: string;
  units?: string;
  [key: string]: any;
}

interface WeatherData {
  name: string;
  main: {
    temp: number;
    feels_like: number;
    humidity: number;
  };
  weather: Array<{
    description: string;
    icon: string;
  }>;
}

interface Props {
  config: WeatherConfig;
  workspaceId?: number;
  notebookId?: number;
}

const props = defineProps<Props>();

const loading = ref(false);
const error = ref<string | null>(null);
const weather = ref<WeatherData | null>(null);

const unitSymbol = computed(() => {
  const units = props.config.units || "imperial";
  return units === "metric" ? "C" : units === "kelvin" ? "K" : "F";
});

const weatherIcon = computed(() => {
  if (!weather.value?.weather[0]?.icon) return "☀️";
  const icon = weather.value.weather[0].icon;
  // Map OpenWeatherMap icons to emoji
  const iconMap: Record<string, string> = {
    "01d": "☀️",
    "01n": "🌙",
    "02d": "⛅",
    "02n": "☁️",
    "03d": "☁️",
    "03n": "☁️",
    "04d": "☁️",
    "04n": "☁️",
    "09d": "🌧️",
    "09n": "🌧️",
    "10d": "🌦️",
    "10n": "🌧️",
    "11d": "⛈️",
    "11n": "⛈️",
    "13d": "🌨️",
    "13n": "🌨️",
    "50d": "🌫️",
    "50n": "🌫️",
  };
  return iconMap[icon] || "☀️";
});

async function fetchWeather() {
  if (!props.workspaceId || !props.config.location) {
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const token = localStorage.getItem("access_token");
    if (!token) {
      error.value = "Not authenticated";
      return;
    }

    // Step 1: Geocode the location to get coordinates
    const geoResponse = await fetch(
      `/api/v1/integrations/weather-api/execute?workspace_id=${props.workspaceId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          endpoint_id: "geocode",
          parameters: {
            q: props.config.location,
            limit: 1,
          },
        }),
      },
    );

    if (!geoResponse.ok) {
      const data = await geoResponse.json().catch(() => ({}));
      throw new Error(data.detail || `Geocoding failed: HTTP ${geoResponse.status}`);
    }

    const geoResult = await geoResponse.json();
    const geoData = geoResult.data;

    if (!geoData || geoData.length === 0) {
      throw new Error(`Location not found: ${props.config.location}`);
    }

    const { lat, lon } = geoData[0];

    // Step 2: Fetch weather using coordinates
    const weatherResponse = await fetch(
      `/api/v1/integrations/weather-api/execute?workspace_id=${props.workspaceId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          endpoint_id: "current_weather",
          parameters: {
            lat,
            lon,
          },
        }),
      },
    );

    if (!weatherResponse.ok) {
      const data = await weatherResponse.json().catch(() => ({}));
      throw new Error(data.detail || `Weather fetch failed: HTTP ${weatherResponse.status}`);
    }

    const result = await weatherResponse.json();
    weather.value = result.data;
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to fetch weather";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchWeather();
});
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

.block-note {
  margin-top: var(--spacing-md, 12px);
  padding: var(--spacing-sm, 8px);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
}

.not-configured .units {
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-secondary, #6b7280);
  margin-bottom: var(--spacing-sm, 8px);
}
</style>
