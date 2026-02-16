<template>
  <div class="calendar-view p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl m-0" style="color: var(--notebook-text)">Google Calendar</h1>
      <div class="flex items-center gap-3">
        <span v-if="connectedEmail" class="text-sm" style="color: var(--pen-gray)">
          {{ connectedEmail }}
        </span>
        <button
          v-if="isConnected"
          class="notebook-button px-3 py-1.5 border-none rounded text-sm cursor-pointer"
          @click="disconnect"
        >
          Disconnect
        </button>
      </div>
    </div>

    <!-- Not connected state -->
    <div
      v-if="!isConnected && !loading"
      class="notebook-page p-8 rounded-lg text-center"
    >
      <p class="mb-4 text-base" style="color: var(--notebook-text)">
        Connect your Google account to view your calendar events.
      </p>
      <button
        class="google-connect-button px-4 py-2.5 rounded text-sm cursor-pointer border-none inline-flex items-center gap-2"
        @click="connectGoogle"
        :disabled="connectLoading"
      >
        <svg width="18" height="18" viewBox="0 0 48 48">
          <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
          <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
          <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
          <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
        </svg>
        {{ connectLoading ? "Connecting..." : "Connect Google Calendar" }}
      </button>
    </div>

    <!-- Connected: calendar controls -->
    <div v-if="isConnected" class="mb-4 flex items-center gap-3 flex-wrap">
      <select
        v-model="selectedCalendarId"
        class="auth-input px-3 py-1.5 rounded text-sm"
        @change="fetchEvents"
      >
        <option v-for="cal in calendars" :key="cal.id" :value="cal.id">
          {{ cal.summary }}{{ cal.primary ? " (Primary)" : "" }}
        </option>
      </select>
      <button
        class="notebook-button px-3 py-1.5 border-none rounded text-sm cursor-pointer"
        @click="prevPeriod"
      >
        &larr; Previous
      </button>
      <span class="text-sm font-medium" style="color: var(--notebook-text)">
        {{ formatDateRange(viewStart, viewEnd) }}
      </span>
      <button
        class="notebook-button px-3 py-1.5 border-none rounded text-sm cursor-pointer"
        @click="nextPeriod"
      >
        Next &rarr;
      </button>
      <button
        class="notebook-button px-3 py-1.5 border-none rounded text-sm cursor-pointer"
        @click="goToToday"
      >
        Today
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center py-8">
      <p class="text-sm" style="color: var(--pen-gray)">Loading...</p>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="p-3 rounded text-sm mb-4"
      style="
        color: var(--pen-red);
        background: color-mix(in srgb, var(--pen-red) 10%, transparent);
      "
    >
      {{ error }}
    </div>

    <!-- Events list -->
    <div v-if="isConnected && !loading && events.length > 0" class="events-list">
      <div
        v-for="(dayEvents, date) in groupedEvents"
        :key="date"
        class="mb-4"
      >
        <h3 class="text-sm font-semibold mb-2 pb-1" style="color: var(--notebook-accent); border-bottom: 1px solid var(--page-border)">
          {{ formatDayHeader(date as string) }}
        </h3>
        <div
          v-for="event in dayEvents"
          :key="event.id ?? undefined"
          class="event-card notebook-page p-3 rounded mb-2 cursor-pointer hover:shadow-md transition-shadow"
          @click="event.html_link && openEvent(event.html_link)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <p class="m-0 text-sm font-medium truncate" style="color: var(--notebook-text)">
                {{ event.summary }}
              </p>
              <p class="m-0 mt-1 text-xs" style="color: var(--pen-gray)">
                {{ formatEventTime(event) }}
              </p>
              <p
                v-if="event.location"
                class="m-0 mt-1 text-xs truncate"
                style="color: var(--pen-gray)"
              >
                {{ event.location }}
              </p>
            </div>
            <span
              v-if="event.status === 'confirmed'"
              class="text-xs px-1.5 py-0.5 rounded shrink-0"
              style="background: color-mix(in srgb, var(--pen-green, #2d6a4f) 15%, transparent); color: var(--pen-green, #2d6a4f)"
            >
              confirmed
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- No events -->
    <div
      v-if="isConnected && !loading && events.length === 0 && !error"
      class="text-center py-8"
    >
      <p class="text-sm" style="color: var(--pen-gray)">No events found in this time period.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { oauthService } from "../services/oauth"
import { calendarService, type Calendar, type CalendarEvent } from "../services/calendar"

const loading = ref(true)
const connectLoading = ref(false)
const error = ref<string | null>(null)
const isConnected = ref(false)
const connectedEmail = ref<string | null>(null)
const calendars = ref<Calendar[]>([])
const selectedCalendarId = ref("primary")
const events = ref<CalendarEvent[]>([])
const viewStart = ref(new Date())
const viewEnd = ref(new Date())

// Initialize date range to current week (Monday to Sunday)
function initDateRange() {
  const now = new Date()
  const dayOfWeek = now.getDay()
  const monday = new Date(now)
  monday.setDate(now.getDate() - ((dayOfWeek + 6) % 7))
  monday.setHours(0, 0, 0, 0)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  sunday.setHours(23, 59, 59, 999)
  viewStart.value = monday
  viewEnd.value = sunday
}

const groupedEvents = computed(() => {
  const groups: Record<string, CalendarEvent[]> = {}
  for (const event of events.value) {
    let dateStr = "unknown"
    if (event.start) {
      const parts = event.start.split("T")
      dateStr = event.all_day ? event.start : (parts[0] ?? event.start)
    }
    const existing = groups[dateStr]
    if (existing) {
      existing.push(event)
    } else {
      groups[dateStr] = [event]
    }
  }
  return groups
})

function formatDayHeader(dateStr: string): string {
  if (dateStr === "unknown") return "Unknown Date"
  const date = new Date(dateStr + (dateStr.includes("T") ? "" : "T00:00:00"))
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

function formatEventTime(event: CalendarEvent): string {
  if (event.all_day) return "All day"
  if (!event.start) return ""
  const start = new Date(event.start)
  const timeStr = start.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  })
  if (event.end) {
    const end = new Date(event.end)
    const endStr = end.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    })
    return `${timeStr} - ${endStr}`
  }
  return timeStr
}

function formatDateRange(start: Date, end: Date): string {
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" }
  return `${start.toLocaleDateString(undefined, opts)} - ${end.toLocaleDateString(undefined, opts)}`
}

function prevPeriod() {
  const newStart = new Date(viewStart.value)
  newStart.setDate(newStart.getDate() - 7)
  const newEnd = new Date(viewEnd.value)
  newEnd.setDate(newEnd.getDate() - 7)
  viewStart.value = newStart
  viewEnd.value = newEnd
  fetchEvents()
}

function nextPeriod() {
  const newStart = new Date(viewStart.value)
  newStart.setDate(newStart.getDate() + 7)
  const newEnd = new Date(viewEnd.value)
  newEnd.setDate(newEnd.getDate() + 7)
  viewStart.value = newStart
  viewEnd.value = newEnd
  fetchEvents()
}

function goToToday() {
  initDateRange()
  fetchEvents()
}

function openEvent(url: string) {
  window.open(url, "_blank", "noopener,noreferrer")
}

async function connectGoogle() {
  connectLoading.value = true
  error.value = null
  try {
    const { authorization_url } = await oauthService.getGoogleAuthUrl()
    window.location.href = authorization_url
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to initiate Google connection"
    connectLoading.value = false
  }
}

async function disconnect() {
  try {
    await oauthService.disconnectGoogle()
    isConnected.value = false
    connectedEmail.value = null
    calendars.value = []
    events.value = []
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to disconnect"
  }
}

async function checkConnection() {
  try {
    const connections = await oauthService.listConnections()
    const google = connections.find((c) => c.provider === "google" && c.is_active)
    if (google) {
      isConnected.value = true
      connectedEmail.value = google.provider_email
      return true
    }
  } catch {
    // Not connected
  }
  return false
}

async function fetchCalendars() {
  try {
    calendars.value = await calendarService.listCalendars()
    const primary = calendars.value.find((c) => c.primary)
    if (primary) {
      selectedCalendarId.value = primary.id
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to load calendars"
  }
}

async function fetchEvents() {
  error.value = null
  loading.value = true
  try {
    const result = await calendarService.listEvents({
      calendar_id: selectedCalendarId.value,
      time_min: viewStart.value.toISOString(),
      time_max: viewEnd.value.toISOString(),
    })
    events.value = result.events
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Failed to load events"
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  initDateRange()
  const connected = await checkConnection()
  if (connected) {
    await fetchCalendars()
    await fetchEvents()
  } else {
    loading.value = false
  }
})
</script>

<style scoped>
.auth-input {
  border: 1px solid var(--page-border);
  background: var(--notebook-bg);
  color: var(--notebook-text);
}

.google-connect-button {
  background: #fff;
  color: #3c4043;
  border: 1px solid #dadce0;
  font-weight: 500;
  transition: background 0.2s, box-shadow 0.2s;
}

.google-connect-button:hover:not(:disabled) {
  background: #f8f9fa;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.google-connect-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.event-card {
  border: 1px solid var(--page-border);
}
</style>
