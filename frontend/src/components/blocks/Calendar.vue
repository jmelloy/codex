<template>
  <div class="calendar-block custom-block">
    <div class="calendar-header">
      <span class="calendar-month">{{ monthLabel }}</span>
    </div>
    <div class="calendar-grid">
      <span v-for="wd in weekdayLabels" :key="wd" class="calendar-weekday">{{ wd }}</span>
      <span
        v-for="cell in cells"
        :key="cell.key"
        class="calendar-day"
        :class="{
          'calendar-day-outside': !cell.inMonth,
          'calendar-day-highlighted': cell.highlighted,
        }"
      >
        {{ cell.day }}
      </span>
    </div>
    <div v-if="!parsedDate" class="calendar-error">No valid date provided</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"

interface Props {
  date?: string
  start?: string
  end?: string
}

const props = defineProps<Props>()

const parseDate = (value: string | undefined): Date | null => {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const parsedDate = computed(() => parseDate(props.date) ?? parseDate(props.start))
const parsedEnd = computed(() => parseDate(props.end) ?? parsedDate.value)

const weekdayLabels = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

const monthLabel = computed(() => {
  const d = parsedDate.value ?? new Date()
  return d.toLocaleDateString(undefined, { month: "long", year: "numeric" })
})

interface Cell {
  key: string
  day: number
  inMonth: boolean
  highlighted: boolean
}

const cells = computed<Cell[]>(() => {
  const anchor = parsedDate.value ?? new Date()
  const year = anchor.getFullYear()
  const month = anchor.getMonth()
  const firstOfMonth = new Date(year, month, 1)
  const startOffset = firstOfMonth.getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const start = parsedDate.value
  const end = parsedEnd.value

  const result: Cell[] = []
  for (let i = 0; i < startOffset; i++) {
    result.push({ key: `lead-${i}`, day: 0, inMonth: false, highlighted: false })
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const current = new Date(year, month, day)
    const highlighted =
      !!start && !!end && current >= startOfDay(start) && current <= startOfDay(end)
    result.push({ key: `day-${day}`, day, inMonth: true, highlighted })
  }
  return result
})

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}
</script>

<style scoped>
.calendar-block {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  max-width: 280px;
  margin: var(--spacing-md) 0;
}

.calendar-header {
  text-align: center;
  font-weight: var(--font-semibold);
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  text-align: center;
  font-size: var(--text-sm);
}

.calendar-weekday {
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  padding: var(--spacing-xs) 0;
}

.calendar-day {
  padding: var(--spacing-xs) 0;
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
}

.calendar-day-outside {
  visibility: hidden;
}

.calendar-day-highlighted {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-weight: var(--font-semibold);
}

.calendar-error {
  margin-top: var(--spacing-sm);
  color: var(--color-error);
  font-size: var(--text-sm);
  text-align: center;
}
</style>
