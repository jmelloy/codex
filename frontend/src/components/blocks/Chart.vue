<template>
  <figure class="chart-block custom-block">
    <figcaption v-if="title">{{ title }}</figcaption>
    <svg :viewBox="`0 0 ${W} ${height}`" role="img" :aria-label="title || `${type} chart`">
      <template v-if="type === 'pie'">
        <path v-for="(s, i) in slices" :key="i" :d="s.d" :fill="color(i)"><title>{{ s.label }}: {{ s.value }}</title></path>
      </template>
      <template v-else>
        <line :x1="PAD" :y1="height - PAD" :x2="W - PAD" :y2="height - PAD" stroke="currentColor" opacity="0.4" />
        <template v-if="type === 'bar'">
          <g v-for="(p, i) in points" :key="i">
            <rect :x="p.x - bw / 2" :y="p.y" :width="bw" :height="height - PAD - p.y" :fill="color(0)"><title>{{ p.label }}: {{ p.value }}</title></rect>
            <text :x="p.x" :y="height - 6" text-anchor="middle" font-size="11" fill="currentColor">{{ p.label }}</text>
          </g>
        </template>
        <template v-else>
          <polyline :points="points.map((p) => `${p.x},${p.y}`).join(' ')" fill="none" :stroke="color(0)" stroke-width="2" />
          <g v-for="(p, i) in points" :key="i">
            <circle :cx="p.x" :cy="p.y" r="3" :fill="color(0)"><title>{{ p.label }}: {{ p.value }}</title></circle>
            <text :x="p.x" :y="height - 6" text-anchor="middle" font-size="11" fill="currentColor">{{ p.label }}</text>
          </g>
        </template>
      </template>
    </svg>
    <div v-if="type === 'pie'" class="legend">
      <span v-for="(s, i) in slices" :key="i"><i :style="{ background: color(i) }" />{{ s.label }}</span>
    </div>
    <div v-if="!rows.length" class="chart-error">No valid data</div>
  </figure>
</template>

<script setup lang="ts">
import { computed } from "vue"

const props = withDefaults(defineProps<{ type?: string; data: unknown; title?: string; height?: number }>(), {
  type: "bar",
  title: undefined,
  height: 240,
})

const W = 480
const PAD = 24
const PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#9c755f"]
const color = (i: number) => PALETTE[i % PALETTE.length]

const rows = computed(() =>
  (Array.isArray(props.data) ? props.data : [])
    .map((d) => ({ label: String(d?.label ?? ""), value: Number(d?.value) }))
    .filter((d) => Number.isFinite(d.value))
    .slice(0, 200),
)

const bw = computed(() => Math.max(4, ((W - 2 * PAD) / Math.max(rows.value.length, 1)) * 0.6))

const points = computed(() => {
  const n = rows.value.length
  const max = Math.max(...rows.value.map((r) => r.value), 0) || 1
  const min = Math.min(...rows.value.map((r) => r.value), 0)
  const span = max - min || 1
  const plotH = props.height - 2 * PAD
  return rows.value.map((r, i) => ({
    ...r,
    x: PAD + ((i + 0.5) * (W - 2 * PAD)) / n,
    y: PAD + plotH - ((r.value - min) / span) * plotH,
  }))
})

const slices = computed(() => {
  const vals = rows.value.map((r) => ({ ...r, value: Math.max(r.value, 0) }))
  const total = vals.reduce((a, r) => a + r.value, 0)
  if (!total) return []
  const r = Math.min(props.height, W) / 2 - 8
  const cx = W / 2
  const cy = props.height / 2
  let angle = -Math.PI / 2
  return vals.map((v) => {
    const frac = v.value / total
    const end = angle + Math.min(frac, 0.99999) * 2 * Math.PI
    const large = frac > 0.5 ? 1 : 0
    const d = `M${cx},${cy} L${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)} A${r},${r} 0 ${large} 1 ${cx + r * Math.cos(end)},${cy + r * Math.sin(end)} Z`
    angle = end
    return { ...v, d }
  })
})
</script>

<style scoped>
.chart-block { margin: var(--spacing-md) 0; max-width: 480px; }
.chart-block svg { width: 100%; color: var(--color-text-primary); }
.chart-block figcaption { font-weight: var(--font-semibold); }
.legend { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); font-size: var(--text-sm); }
.legend i { display: inline-block; width: 10px; height: 10px; margin-right: 4px; }
.chart-error { color: var(--color-error); font-size: var(--text-sm); }
</style>
