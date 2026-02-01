<template>
  <div class="chart-block">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Chart, registerables } from 'chart.js'

// Register Chart.js components
Chart.register(...registerables)

interface Props {
  type?: 'bar' | 'line' | 'pie' | 'doughnut'
  data?: any
}

const props = withDefaults(defineProps<Props>(), {
  type: 'bar',
  data: () => ({
    labels: ['January', 'February', 'March', 'April', 'May'],
    datasets: [{
      label: 'Sample Data',
      data: [12, 19, 3, 5, 2],
      backgroundColor: 'rgba(54, 162, 235, 0.5)',
    }]
  })
})

const chartCanvas = ref<HTMLCanvasElement | null>(null)

onMounted(() => {
  if (chartCanvas.value) {
    new Chart(chartCanvas.value, {
      type: props.type,
      data: props.data,
      options: {
        responsive: true,
        maintainAspectRatio: false
      }
    })
  }
})
</script>

<style scoped>
.chart-block {
  width: 100%;
  height: 400px;
  padding: 1rem;
}
</style>
