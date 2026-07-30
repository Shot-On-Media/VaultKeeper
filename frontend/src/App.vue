<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { useDashboardStore } from './stores/dashboard'
import { useNotificationStore } from './stores/notification'
import { useRepositoryStore } from './stores/repository'
import { useRestoreStore } from './stores/restore'
import { useSchedulerStore } from './stores/scheduler'
import { useSnapshotStore } from './stores/snapshot'
import { useStorageStore } from './stores/storage'
import { useVerificationStore } from './stores/verification'

const route = useRoute()
const dashboardStore = useDashboardStore()
const storageStore = useStorageStore()
const repositoryStore = useRepositoryStore()
const snapshotStore = useSnapshotStore()
const restoreStore = useRestoreStore()
const schedulerStore = useSchedulerStore()
const verificationStore = useVerificationStore()
const notificationStore = useNotificationStore()

const pageTitle = computed(() => String(route.meta.title ?? 'Dashboard'))
const failedSignals = computed(
  () =>
    (dashboardStore.summary?.jobs.failed ?? 0) +
    (dashboardStore.summary?.restores.failed ?? 0) +
    verificationStore.reports.filter((report) => report.status === 'failed').length +
    notificationStore.deliveries.filter((delivery) => delivery.status === 'failed')
      .length,
)

onMounted(() => {
  void dashboardStore.loadDashboard()
  void storageStore.loadStorage()
  void repositoryStore.loadRepositories()
  void snapshotStore.loadSnapshots()
  void restoreStore.loadRestores()
  void schedulerStore.loadScheduler()
  void verificationStore.loadReports()
  void notificationStore.loadNotifications()
})
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">VaultKeeper</p>
        <h1>{{ pageTitle }}</h1>
      </div>
      <nav class="nav-list" aria-label="Primary">
        <RouterLink class="nav-item" to="/">Dashboard</RouterLink>
        <RouterLink class="nav-item" to="/backups">Backups</RouterLink>
        <RouterLink class="nav-item" to="/restore">Restore</RouterLink>
        <RouterLink class="nav-item" to="/scheduler">Scheduler</RouterLink>
        <RouterLink class="nav-item" to="/settings">Settings</RouterLink>
      </nav>
      <dl class="summary-list">
        <div>
          <dt>Storage</dt>
          <dd>{{ storageStore.items.length }}</dd>
        </div>
        <div>
          <dt>Repositories</dt>
          <dd>{{ repositoryStore.items.length }}</dd>
        </div>
        <div>
          <dt>Snapshots</dt>
          <dd>{{ snapshotStore.items.length }}</dd>
        </div>
        <div>
          <dt>Restores</dt>
          <dd>{{ restoreStore.items.length }}</dd>
        </div>
        <div>
          <dt>Schedules</dt>
          <dd>{{ schedulerStore.policies.length }}</dd>
        </div>
        <div>
          <dt>Signals</dt>
          <dd>{{ failedSignals }}</dd>
        </div>
      </dl>
    </aside>

    <section class="workspace">
      <RouterView />
    </section>
  </main>
</template>
