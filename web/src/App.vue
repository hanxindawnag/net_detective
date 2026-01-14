<template>
  <div class="container">
    <h1>Net Detective Dashboard</h1>

    <section class="section">
      <h2>Targets Overview</h2>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>URL</th>
            <th>Status</th>
            <th>Latest RT (ms)</th>
            <th>Last Seen</th>
            <th>Availability</th>
            <th>Avg RT (ms)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="target in targets" :key="target.id">
            <td>{{ target.name }}</td>
            <td>{{ target.url }}</td>
            <td>{{ target.latest_status_code ?? '-' }}</td>
            <td>{{ formatNumber(target.latest_response_time_ms) }}</td>
            <td>{{ target.latest_ts ?? '-' }}</td>
            <td>{{ formatPercent(target.availability) }}</td>
            <td>{{ formatNumber(target.avg_response_time_ms) }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="section grid">
      <div class="panel">
        <div class="panel-header">
          <h2>Response Time (60m)</h2>
          <select v-model.number="selectedTargetId" @change="refreshMetrics">
            <option v-for="target in targets" :key="target.id" :value="target.id">
              {{ target.name }}
            </option>
          </select>
        </div>
        <div ref="chartRef" class="chart"></div>
      </div>

      <div class="panel">
        <h2>Availability (24h)</h2>
        <div class="availability">
          {{ formatPercent(availability) }}
        </div>
        <h2>Recent Alerts</h2>
        <ul class="alerts">
          <li v-for="alert in alerts" :key="alert.id">
            [{{ alert.ts }}] Target {{ alert.target_id }} - {{ alert.message }}
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const targets = ref([])
const selectedTargetId = ref(null)
const availability = ref(null)
const alerts = ref([])
const chartRef = ref(null)
let chartInstance = null
let poller = null

const formatNumber = (value) => {
  if (value === null || value === undefined) {
    return '-'
  }
  return Number(value).toFixed(1)
}

const formatPercent = (value) => {
  if (value === null || value === undefined) {
    return '-'
  }
  return `${(value * 100).toFixed(1)}%`
}

const fetchOverview = async () => {
  const response = await axios.get('/api/dashboard/overview')
  targets.value = response.data.targets
  if (!selectedTargetId.value && targets.value.length > 0) {
    selectedTargetId.value = targets.value[0].id
  }
}

const fetchTimeseries = async () => {
  if (!selectedTargetId.value) return
  const response = await axios.get('/api/dashboard/timeseries', {
    params: { target_id: selectedTargetId.value, minutes: 60 }
  })
  const series = response.data.series
  const xData = series.map((point) => point.ts)
  const yData = series.map((point) => point.response_time_ms)
  chartInstance.setOption({
    xAxis: { type: 'category', data: xData },
    yAxis: { type: 'value' },
    series: [{ data: yData, type: 'line', smooth: false }],
    tooltip: { trigger: 'axis' }
  })
}

const fetchAvailability = async () => {
  if (!selectedTargetId.value) return
  const response = await axios.get('/api/dashboard/availability', {
    params: { target_id: selectedTargetId.value, hours: 24 }
  })
  availability.value = response.data.availability
}

const fetchAlerts = async () => {
  const response = await axios.get('/api/alerts', { params: { limit: 20 } })
  alerts.value = response.data.alerts
}

const refreshMetrics = async () => {
  await Promise.all([fetchTimeseries(), fetchAvailability(), fetchAlerts()])
}

onMounted(async () => {
  chartInstance = echarts.init(chartRef.value)
  await fetchOverview()
  await refreshMetrics()
  poller = setInterval(async () => {
    await fetchOverview()
    await refreshMetrics()
  }, 5000)
})

onBeforeUnmount(() => {
  if (poller) {
    clearInterval(poller)
  }
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.container {
  font-family: Arial, sans-serif;
  padding: 24px;
  color: #1f2933;
}

.section {
  margin-bottom: 24px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

table th,
table td {
  border: 1px solid #d3dce6;
  padding: 8px;
  text-align: left;
}

.grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.panel {
  background: #f7f9fc;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e0e7ff;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.chart {
  height: 320px;
}

.availability {
  font-size: 32px;
  font-weight: bold;
  margin: 12px 0 24px;
}

.alerts {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 13px;
}

.alerts li {
  margin-bottom: 8px;
}
</style>
