<template>
  <div class="livedata-block custom-block">
    <span v-if="label" class="livedata-label">{{ label }}: </span>
    <span v-if="error" class="livedata-error">{{ error }}</span>
    <span v-else class="livedata-value">{{ display }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

const props = withDefaults(
  defineProps<{ src: string; path?: string; label?: string; interval?: number; format?: string }>(),
  { path: undefined, label: undefined, interval: 30, format: "text" },
)

const value = ref<unknown>(null)
const error = ref("")
let timer: ReturnType<typeof setInterval> | undefined
let controller: AbortController | undefined

function pick(data: unknown, path?: string): unknown {
  if (!path) return data
  return path.split(".").reduce<unknown>((cur, key) => {
    if (cur === null || typeof cur !== "object" || key === "__proto__" || key === "constructor") return undefined
    return (cur as Record<string, unknown>)[key]
  }, data)
}

async function load() {
  controller?.abort()
  controller = new AbortController()
  try {
    // credentials omitted: cross-origin endpoints never see the user's session.
    const res = await fetch(props.src, { signal: controller.signal, credentials: "omit" })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    value.value = pick(await res.json(), props.path)
    error.value = ""
  } catch (e) {
    if ((e as Error).name !== "AbortError") error.value = `Failed to load: ${(e as Error).message}`
  }
}

const display = computed(() => {
  const v = value.value
  if (v === null || v === undefined) return "…"
  if (props.format === "number") return Number.isFinite(Number(v)) ? Number(v).toLocaleString() : "NaN"
  if (props.format === "json" || typeof v === "object") return JSON.stringify(v)
  return String(v)
})

onMounted(() => {
  load()
  timer = setInterval(load, props.interval * 1000)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  controller?.abort()
})
</script>

<style scoped>
.livedata-block { margin: var(--spacing-md) 0; }
.livedata-value { font-weight: var(--font-semibold); }
.livedata-error { color: var(--color-error); font-size: var(--text-sm); }
</style>
