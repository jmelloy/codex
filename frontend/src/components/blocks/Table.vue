<template>
  <table class="table-block custom-block">
    <caption v-if="caption">{{ caption }}</caption>
    <thead v-if="Array.isArray(columns)">
      <tr><th v-for="(c, i) in columns" :key="i">{{ c }}</th></tr>
    </thead>
    <tbody>
      <tr v-for="(row, r) in safeRows" :key="r">
        <td v-for="(cell, c) in row" :key="c">{{ cell }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{ columns?: unknown; rows: unknown; caption?: string }>()

const safeRows = computed<unknown[][]>(() =>
  Array.isArray(props.rows) ? props.rows.map((r) => (Array.isArray(r) ? r : [r])) : [],
)
</script>

<style scoped>
.table-block { border-collapse: collapse; margin: var(--spacing-md) 0; }
.table-block th, .table-block td { border: 1px solid var(--color-border-light); padding: var(--spacing-xs) var(--spacing-sm); text-align: left; }
.table-block th { background: var(--color-bg-secondary); }
</style>
