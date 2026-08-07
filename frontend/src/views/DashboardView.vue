<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { DashboardMetric, useDashboardStore } from '../stores/dashboard'

const dashboardStore = useDashboardStore()

const systemPosture = computed(() => {
  const summary = dashboardStore.summary
  if (summary === null) {
    return 'Loading'
  }
  if (
    summary.storage.failed > 0 ||
    summary.repositories.failed > 0 ||
    summary.snapshots.failed > 0 ||
    summary.jobs.failed > 0 ||
    summary.restores.failed > 0 ||
    summary.verification.failed > 0
  ) {
    return 'Attention'
  }
  if (
    summary.storage.warning > 0 ||
    summary.repositories.warning > 0 ||
    summary.jobs.retrying > 0 ||
    summary.verification.warning > 0
  ) {
    return 'Watch'
  }
  return 'Healthy'
})

onMounted(() => {
  void dashboardStore.loadDashboard()
})

function dashboardHealthClass(metric: DashboardMetric): string {
  if (metric.failed > 0) {
    return 'failed'
  }
  if (metric.warning > 0) {
    return 'warning'
  }
  return 'passed'
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`
  }
  const units = ['KB', 'MB', 'GB', 'TB']
  let size = value / 1024
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}
</script>

<template>
  <header class="page-header">
    <div>
      <p class="eyebrow">Overview</p>
      <h2>System Dashboard</h2>
    </div>
    <button class="secondary-button" type="button" @click="dashboardStore.loadDashboard()">
      Refresh
    </button>
  </header>

  <div v-if="dashboardStore.error" class="notice error">{{ dashboardStore.error }}</div>

  <section class="dashboard-panel" aria-label="Operational dashboard">
    <div v-if="dashboardStore.loading && dashboardStore.summary === null" class="notice">
      Loading dashboard...
    </div>
    <template v-else-if="dashboardStore.summary">
      <div class="dashboard-status">
        <div>
          <p class="eyebrow">System Health</p>
          <strong>{{ systemPosture }}</strong>
        </div>
        <span :class="['status-pill', systemPosture.toLowerCase()]">
          {{ systemPosture }}
        </span>
      </div>

      <div class="dashboard-grid">
        <article class="metric-card">
          <span :class="['status-pill', dashboardHealthClass(dashboardStore.summary.storage)]">
            Storage
          </span>
          <strong>{{ dashboardStore.summary.storage.healthy }}</strong>
          <span>
            {{ dashboardStore.summary.storage.total }} total /
            {{ dashboardStore.summary.storage.failed }} failed
          </span>
        </article>
        <article class="metric-card">
          <span
            :class="[
              'status-pill',
              dashboardHealthClass(dashboardStore.summary.repositories),
            ]"
          >
            Repositories
          </span>
          <strong>{{ dashboardStore.summary.repositories.healthy }}</strong>
          <span>
            {{ dashboardStore.summary.repositories.total }} total /
            {{ dashboardStore.summary.repositories.failed }} failed
          </span>
        </article>
        <article class="metric-card">
          <span class="status-pill completed">Snapshots</span>
          <strong>{{ dashboardStore.summary.snapshots.completed }}</strong>
          <span>
            {{ dashboardStore.summary.snapshots.total }} total /
            {{ formatBytes(dashboardStore.summary.snapshots.total_bytes) }}
          </span>
        </article>
        <article class="metric-card">
          <span :class="['status-pill', dashboardStore.summary.jobs.failed > 0 ? 'failed' : 'passed']">
            Jobs
          </span>
          <strong>{{ dashboardStore.summary.jobs.running }}</strong>
          <span>
            {{ dashboardStore.summary.jobs.queued }} queued /
            {{ dashboardStore.summary.jobs.failed }} failed
          </span>
        </article>
        <article class="metric-card">
          <span
            :class="[
              'status-pill',
              dashboardStore.summary.restores.failed > 0 ? 'failed' : 'passed',
            ]"
          >
            Restores
          </span>
          <strong>{{ dashboardStore.summary.restores.completed }}</strong>
          <span>
            {{ dashboardStore.summary.restores.total }} total /
            {{ dashboardStore.summary.restores.failed }} failed
          </span>
        </article>
        <article class="metric-card">
          <span
            :class="[
              'status-pill',
              dashboardStore.summary.verification.failed > 0
                ? 'failed'
                : dashboardStore.summary.verification.warning > 0
                  ? 'warning'
                  : 'passed',
            ]"
          >
            Verification
          </span>
          <strong>{{ dashboardStore.summary.verification.passed }}</strong>
          <span>
            {{ dashboardStore.summary.verification.total }} reports /
            {{ dashboardStore.summary.verification.failed }} failed
          </span>
        </article>
      </div>
    </template>
  </section>

  <section class="table-panel" aria-label="Recent restores">
    <div class="section-heading">
      <h3>Recent Restores</h3>
    </div>
    <div
      v-if="dashboardStore.summary?.recent_restores.length === 0"
      class="empty-state"
    >
      No restore history yet.
    </div>
    <table v-else-if="dashboardStore.summary">
      <thead>
        <tr>
          <th>Restore</th>
          <th>Status</th>
          <th>Target</th>
          <th>Completed</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="restore in dashboardStore.summary.recent_restores" :key="restore.uuid">
          <td>
            <strong>{{ restore.uuid }}</strong>
            <span>{{ restore.snapshot_uuid }}</span>
          </td>
          <td>
            <span :class="['status-pill', restore.status]">{{ restore.status }}</span>
          </td>
          <td>{{ restore.target_path }}</td>
          <td>
            {{
              restore.completed_at
                ? new Date(restore.completed_at).toLocaleString()
                : 'Not completed'
            }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
