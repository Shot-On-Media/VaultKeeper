<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { DashboardMetric, useDashboardStore } from '../stores/dashboard'
import {
  NotificationChannel,
  NotificationDriver,
  useNotificationStore,
} from '../stores/notification'
import { RepositoryLocation, useRepositoryStore } from '../stores/repository'
import { useRestoreStore } from '../stores/restore'
import { useSchedulerStore } from '../stores/scheduler'
import { useSnapshotStore } from '../stores/snapshot'
import { StorageLocation, useStorageStore } from '../stores/storage'
import { useVerificationStore } from '../stores/verification'

const storageStore = useStorageStore()
const dashboardStore = useDashboardStore()
const notificationStore = useNotificationStore()
const repositoryStore = useRepositoryStore()
const restoreStore = useRestoreStore()
const schedulerStore = useSchedulerStore()
const snapshotStore = useSnapshotStore()
const verificationStore = useVerificationStore()
const editingUuid = ref<string | null>(null)
const editingRepositoryUuid = ref<string | null>(null)
const form = reactive({
  name: '',
  path: '',
})
const repositoryForm = reactive({
  name: '',
  storageUuid: '',
})
const snapshotForm = reactive({
  repositoryUuid: '',
  engine: 'framework',
  source: '',
})
const mariaDBForm = reactive({
  repositoryUuid: '',
  databaseName: '',
})
const policyForm = reactive({
  name: '',
  repositoryUuid: '',
  engine: 'filesystem' as const,
  source: '',
  intervalMinutes: 60,
  nextRunAt: new Date(Date.now() + 60000).toISOString().slice(0, 16),
  maxRetries: 2,
})
const restoreForm = reactive({
  snapshotUuid: '',
  targetPath: '',
})
const notificationForm = reactive({
  name: '',
  driver: 'ntfy' as NotificationDriver,
  enabled: true,
  serverUrl: '',
  topic: '',
  token: '',
  url: '',
  recipient: '',
})
const editingNotificationUuid = ref<string | null>(null)

const hasStorage = computed(() => storageStore.items.length > 0)
const hasRepositories = computed(() => repositoryStore.items.length > 0)
const hasSnapshots = computed(() => snapshotStore.items.length > 0)
const validCount = computed(
  () => storageStore.items.filter((item) => item.status === 'valid').length,
)
const invalidCount = computed(
  () => storageStore.items.filter((item) => item.status === 'invalid').length,
)
const validRepositoryCount = computed(
  () => repositoryStore.items.filter((item) => item.status === 'valid').length,
)
const completedSnapshotCount = computed(
  () => snapshotStore.items.filter((item) => item.status === 'completed').length,
)
const completedSnapshots = computed(() =>
  snapshotStore.items.filter((item) => item.status === 'completed'),
)
const hasRestores = computed(() => restoreStore.items.length > 0)
const completedRestoreCount = computed(
  () => restoreStore.items.filter((item) => item.status === 'completed').length,
)
const failedVerificationCount = computed(
  () => verificationStore.reports.filter((item) => item.status === 'failed').length,
)
const failedNotificationCount = computed(
  () => notificationStore.deliveries.filter((item) => item.status === 'failed').length,
)
const runningJobCount = computed(
  () => schedulerStore.jobs.filter((item) => item.status === 'running').length,
)
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
  void storageStore.loadStorage()
  void repositoryStore.loadRepositories()
  void snapshotStore.loadSnapshots()
  void snapshotStore.loadMariaDBDatabases()
  void restoreStore.loadRestores()
  void schedulerStore.loadScheduler()
  void verificationStore.loadReports()
  void notificationStore.loadNotifications()
})

function resetForm(): void {
  editingUuid.value = null
  form.name = ''
  form.path = ''
}

function editStorage(storage: StorageLocation): void {
  editingUuid.value = storage.uuid
  form.name = storage.name
  form.path = storage.config.path
}

async function saveStorage(): Promise<void> {
  if (editingUuid.value === null) {
    await storageStore.createStorage(form)
  } else {
    await storageStore.updateStorage(editingUuid.value, form)
  }
  resetForm()
}

async function deleteStorage(storageUuid: string): Promise<void> {
  await storageStore.deleteStorage(storageUuid)
  if (editingUuid.value === storageUuid) {
    resetForm()
  }
}

function storageName(storageUuid: string): string {
  return storageStore.items.find((storage) => storage.uuid === storageUuid)?.name ?? storageUuid
}

function repositoryName(repositoryUuid: string): string {
  return (
    repositoryStore.items.find((repository) => repository.uuid === repositoryUuid)?.name ??
    repositoryUuid
  )
}

function snapshotLabel(snapshotUuid: string): string {
  const snapshot = snapshotStore.items.find((item) => item.uuid === snapshotUuid)
  if (snapshot === undefined) {
    return snapshotUuid
  }
  return `${snapshot.engine} - ${snapshot.source}`
}

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

function resetNotificationForm(): void {
  editingNotificationUuid.value = null
  notificationForm.name = ''
  notificationForm.driver = 'ntfy'
  notificationForm.enabled = true
  notificationForm.serverUrl = ''
  notificationForm.topic = ''
  notificationForm.token = ''
  notificationForm.url = ''
  notificationForm.recipient = ''
}

function editNotification(channel: NotificationChannel): void {
  editingNotificationUuid.value = channel.uuid
  notificationForm.name = channel.name
  notificationForm.driver = channel.driver
  notificationForm.enabled = channel.enabled
  notificationForm.serverUrl = String(channel.config.server_url ?? '')
  notificationForm.topic = String(channel.config.topic ?? '')
  notificationForm.token = ''
  notificationForm.url = String(channel.config.url ?? '')
  notificationForm.recipient = String(channel.config.recipient ?? '')
}

async function saveNotification(): Promise<void> {
  if (editingNotificationUuid.value === null) {
    await notificationStore.createChannel(notificationForm)
  } else {
    await notificationStore.updateChannel(
      editingNotificationUuid.value,
      notificationForm,
    )
  }
  resetNotificationForm()
}

function resetRepositoryForm(): void {
  editingRepositoryUuid.value = null
  repositoryForm.name = ''
  repositoryForm.storageUuid = ''
}

function editRepository(repository: RepositoryLocation): void {
  editingRepositoryUuid.value = repository.uuid
  repositoryForm.name = repository.name
  repositoryForm.storageUuid = repository.storage_uuid
}

async function saveRepository(): Promise<void> {
  if (editingRepositoryUuid.value === null) {
    await repositoryStore.createRepository(repositoryForm)
  } else {
    await repositoryStore.updateRepository(editingRepositoryUuid.value, repositoryForm.name)
  }
  resetRepositoryForm()
}

async function deleteRepository(repositoryUuid: string): Promise<void> {
  await repositoryStore.deleteRepository(repositoryUuid)
  if (editingRepositoryUuid.value === repositoryUuid) {
    resetRepositoryForm()
  }
}

function resetSnapshotForm(): void {
  snapshotForm.repositoryUuid = ''
  snapshotForm.engine = 'framework'
  snapshotForm.source = ''
}

function resetMariaDBForm(): void {
  mariaDBForm.repositoryUuid = ''
  mariaDBForm.databaseName = ''
}

async function registerSnapshot(): Promise<void> {
  await snapshotStore.registerSnapshot(snapshotForm)
  resetSnapshotForm()
}

async function runFilesystemBackup(): Promise<void> {
  await snapshotStore.runFilesystemBackup({
    repositoryUuid: snapshotForm.repositoryUuid,
    sourcePath: snapshotForm.source,
  })
  resetSnapshotForm()
}

async function runMariaDBBackup(): Promise<void> {
  await snapshotStore.runMariaDBBackup(mariaDBForm)
  resetMariaDBForm()
}

function resetPolicyForm(): void {
  policyForm.name = ''
  policyForm.repositoryUuid = ''
  policyForm.engine = 'filesystem'
  policyForm.source = ''
  policyForm.intervalMinutes = 60
  policyForm.nextRunAt = new Date(Date.now() + 60000).toISOString().slice(0, 16)
  policyForm.maxRetries = 2
}

async function createPolicy(): Promise<void> {
  await schedulerStore.createPolicy(policyForm)
  resetPolicyForm()
}

function resetRestoreForm(): void {
  restoreForm.snapshotUuid = ''
  restoreForm.targetPath = ''
}

async function createRestore(): Promise<void> {
  await restoreStore.createRestore(restoreForm)
  resetRestoreForm()
}
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">VaultKeeper</p>
        <h1>Storage</h1>
      </div>
      <nav class="nav-list" aria-label="Primary">
        <a class="nav-item active" href="#dashboard">Dashboard</a>
        <a class="nav-item" href="#storage">Storage</a>
        <a class="nav-item" href="#repositories">Repositories</a>
        <a class="nav-item" href="#snapshots">Snapshots</a>
        <a class="nav-item" href="#restores">Restores</a>
        <a class="nav-item" href="#verification">Verification</a>
        <a class="nav-item" href="#notifications">Notifications</a>
        <a class="nav-item" href="#scheduler">Scheduler</a>
      </nav>
      <dl class="summary-list">
        <div>
          <dt>Storage</dt>
          <dd>{{ storageStore.items.length }}</dd>
        </div>
        <div>
          <dt>Storage Valid</dt>
          <dd>{{ validCount }}</dd>
        </div>
        <div>
          <dt>Storage Invalid</dt>
          <dd>{{ invalidCount }}</dd>
        </div>
        <div>
          <dt>Repositories</dt>
          <dd>{{ repositoryStore.items.length }}</dd>
        </div>
        <div>
          <dt>Repo Valid</dt>
          <dd>{{ validRepositoryCount }}</dd>
        </div>
        <div>
          <dt>Snapshots</dt>
          <dd>{{ snapshotStore.items.length }}</dd>
        </div>
        <div>
          <dt>Completed</dt>
          <dd>{{ completedSnapshotCount }}</dd>
        </div>
        <div>
          <dt>Restores</dt>
          <dd>{{ restoreStore.items.length }}</dd>
        </div>
        <div>
          <dt>Restored</dt>
          <dd>{{ completedRestoreCount }}</dd>
        </div>
        <div>
          <dt>Reports</dt>
          <dd>{{ verificationStore.reports.length }}</dd>
        </div>
        <div>
          <dt>Integrity Failed</dt>
          <dd>{{ failedVerificationCount }}</dd>
        </div>
        <div>
          <dt>Notify Failed</dt>
          <dd>{{ failedNotificationCount }}</dd>
        </div>
        <div>
          <dt>Schedules</dt>
          <dd>{{ schedulerStore.policies.length }}</dd>
        </div>
        <div>
          <dt>Running Jobs</dt>
          <dd>{{ runningJobCount }}</dd>
        </div>
      </dl>
    </aside>

    <section class="workspace">
      <header id="dashboard" class="page-header">
        <div>
          <p class="eyebrow">Milestone 9</p>
          <h2>Dashboard</h2>
        </div>
        <button
          class="secondary-button"
          type="button"
          @click="dashboardStore.loadDashboard()"
        >
          Refresh
        </button>
      </header>

      <div v-if="dashboardStore.error" class="notice error">
        {{ dashboardStore.error }}
      </div>

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
              <span
                :class="[
                  'status-pill',
                  dashboardHealthClass(dashboardStore.summary.storage),
                ]"
              >
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
              <span
                :class="[
                  'status-pill',
                  dashboardStore.summary.jobs.failed > 0 ? 'failed' : 'passed',
                ]"
              >
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

          <section class="dashboard-history" aria-label="Recent restore history">
            <div class="section-heading">
              <h3>Recent Restores</h3>
            </div>
            <div
              v-if="dashboardStore.summary.recent_restores.length === 0"
              class="empty-state"
            >
              No restore history yet.
            </div>
            <table v-else>
              <thead>
                <tr>
                  <th>Restore</th>
                  <th>Status</th>
                  <th>Target</th>
                  <th>Completed</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="restore in dashboardStore.summary.recent_restores"
                  :key="restore.uuid"
                >
                  <td>
                    <strong>{{ restore.uuid }}</strong>
                    <span>{{ restore.snapshot_uuid }}</span>
                  </td>
                  <td>
                    <span :class="['status-pill', restore.status]">
                      {{ restore.status }}
                    </span>
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
      </section>

      <header id="storage" class="page-header">
        <div>
          <p class="eyebrow">Milestone 1</p>
          <h2>Storage Locations</h2>
        </div>
        <button class="secondary-button" type="button" @click="storageStore.loadStorage()">
          Refresh
        </button>
      </header>

      <div v-if="storageStore.error" class="notice error">
        {{ storageStore.error }}
      </div>

      <section class="form-panel" aria-label="Storage form">
        <form class="storage-form" @submit.prevent="saveStorage">
          <label>
            <span>Name</span>
            <input v-model="form.name" required maxlength="120" />
          </label>
          <label>
            <span>Local path</span>
            <input v-model="form.path" required placeholder="/backups" />
          </label>
          <div class="form-actions">
            <button class="primary-button" type="submit" :disabled="storageStore.saving">
              {{ editingUuid ? 'Save changes' : 'Create storage' }}
            </button>
            <button
              v-if="editingUuid"
              class="secondary-button"
              type="button"
              @click="resetForm"
            >
              Cancel
            </button>
          </div>
        </form>
      </section>

      <section class="table-panel" aria-label="Storage list">
        <div v-if="storageStore.loading" class="notice">Loading storage locations...</div>
        <div v-else-if="!hasStorage" class="empty-state">
          No storage locations have been created.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Name</th>
              <th>Driver</th>
              <th>Path</th>
              <th>Status</th>
              <th>Last validation</th>
              <th class="actions-column">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="storage in storageStore.items" :key="storage.uuid">
              <td>
                <strong>{{ storage.name }}</strong>
                <span>{{ storage.uuid }}</span>
              </td>
              <td>Local filesystem</td>
              <td>{{ storage.config.path }}</td>
              <td>
                <span :class="['status-pill', storage.status]">
                  {{ storage.status }}
                </span>
                <small v-if="storage.validation_message">
                  {{ storage.validation_message }}
                </small>
              </td>
              <td>
                {{
                  storage.last_validated_at
                    ? new Date(storage.last_validated_at).toLocaleString()
                    : 'Not validated'
                }}
              </td>
              <td class="row-actions">
                <button class="secondary-button" type="button" @click="editStorage(storage)">
                  Edit
                </button>
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="storageStore.validatingUuid === storage.uuid"
                  @click="storageStore.validateStorage(storage.uuid)"
                >
                  Validate
                </button>
                <button
                  class="danger-button"
                  type="button"
                  @click="deleteStorage(storage.uuid)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <header id="repositories" class="page-header">
        <div>
          <p class="eyebrow">Milestone 2</p>
          <h2>Repositories</h2>
        </div>
        <button
          class="secondary-button"
          type="button"
          @click="repositoryStore.loadRepositories()"
        >
          Refresh
        </button>
      </header>

      <div v-if="repositoryStore.error" class="notice error">
        {{ repositoryStore.error }}
      </div>

      <section class="form-panel" aria-label="Repository form">
        <form class="repository-form" @submit.prevent="saveRepository">
          <label>
            <span>Name</span>
            <input v-model="repositoryForm.name" required maxlength="120" />
          </label>
          <label>
            <span>Storage</span>
            <select
              v-model="repositoryForm.storageUuid"
              required
              :disabled="editingRepositoryUuid !== null"
            >
              <option disabled value="">Select storage</option>
              <option
                v-for="storage in storageStore.items"
                :key="storage.uuid"
                :value="storage.uuid"
              >
                {{ storage.name }}
              </option>
            </select>
          </label>
          <div class="form-actions">
            <button
              class="primary-button"
              type="submit"
              :disabled="repositoryStore.saving || !hasStorage"
            >
              {{ editingRepositoryUuid ? 'Save changes' : 'Create repository' }}
            </button>
            <button
              v-if="editingRepositoryUuid"
              class="secondary-button"
              type="button"
              @click="resetRepositoryForm"
            >
              Cancel
            </button>
          </div>
        </form>
      </section>

      <section class="table-panel" aria-label="Repository list">
        <div v-if="repositoryStore.loading" class="notice">Loading repositories...</div>
        <div v-else-if="!hasRepositories" class="empty-state">
          No repositories have been created.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Name</th>
              <th>Storage</th>
              <th>Path</th>
              <th>Status</th>
              <th>Last validation</th>
              <th class="actions-column">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="repository in repositoryStore.items" :key="repository.uuid">
              <td>
                <strong>{{ repository.name }}</strong>
                <span>{{ repository.uuid }}</span>
              </td>
              <td>{{ storageName(repository.storage_uuid) }}</td>
              <td>{{ repository.path }}</td>
              <td>
                <span :class="['status-pill', repository.status]">
                  {{ repository.status }}
                </span>
                <small v-if="repository.validation_message">
                  {{ repository.validation_message }}
                </small>
              </td>
              <td>
                {{
                  repository.last_validated_at
                    ? new Date(repository.last_validated_at).toLocaleString()
                    : 'Not validated'
                }}
              </td>
              <td class="row-actions">
                <button
                  class="secondary-button"
                  type="button"
                  @click="editRepository(repository)"
                >
                  Edit
                </button>
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="repositoryStore.validatingUuid === repository.uuid"
                  @click="repositoryStore.validateRepository(repository.uuid)"
                >
                  Validate
                </button>
                <button
                  class="danger-button"
                  type="button"
                  @click="deleteRepository(repository.uuid)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <header id="snapshots" class="page-header">
        <div>
          <p class="eyebrow">Milestone 3</p>
          <h2>Snapshot History</h2>
        </div>
        <button
          class="secondary-button"
          type="button"
          @click="snapshotStore.loadSnapshots()"
        >
          Refresh
        </button>
      </header>

      <div v-if="snapshotStore.error" class="notice error">
        {{ snapshotStore.error }}
      </div>

      <section class="form-panel" aria-label="Snapshot registration form">
        <form class="snapshot-form" @submit.prevent="registerSnapshot">
          <label>
            <span>Repository</span>
            <select v-model="snapshotForm.repositoryUuid" required>
              <option disabled value="">Select repository</option>
              <option
                v-for="repository in repositoryStore.items"
                :key="repository.uuid"
                :value="repository.uuid"
              >
                {{ repository.name }}
              </option>
            </select>
          </label>
          <label>
            <span>Engine</span>
            <input v-model="snapshotForm.engine" required maxlength="80" />
          </label>
          <label>
            <span>Source</span>
            <input v-model="snapshotForm.source" required placeholder="/srv/data" />
          </label>
          <div class="form-actions">
            <button
              class="secondary-button"
              type="submit"
              :disabled="snapshotStore.saving || !hasRepositories"
            >
              Register snapshot
            </button>
            <button
              class="primary-button"
              type="button"
              :disabled="snapshotStore.saving || !hasRepositories"
              @click="runFilesystemBackup"
            >
              Run filesystem backup
            </button>
          </div>
        </form>
      </section>

      <section class="form-panel" aria-label="MariaDB backup form">
        <form class="mariadb-form" @submit.prevent="runMariaDBBackup">
          <label>
            <span>Repository</span>
            <select v-model="mariaDBForm.repositoryUuid" required>
              <option disabled value="">Select repository</option>
              <option
                v-for="repository in repositoryStore.items"
                :key="repository.uuid"
                :value="repository.uuid"
              >
                {{ repository.name }}
              </option>
            </select>
          </label>
          <label>
            <span>Database</span>
            <select v-model="mariaDBForm.databaseName">
              <option value="">Configured default</option>
              <option
                v-for="databaseName in snapshotStore.mariaDBDatabases"
                :key="databaseName"
                :value="databaseName"
              >
                {{ databaseName }}
              </option>
            </select>
          </label>
          <div class="form-actions">
            <button
              class="primary-button"
              type="submit"
              :disabled="snapshotStore.saving || !hasRepositories"
            >
              Run MariaDB backup
            </button>
            <button
              class="secondary-button"
              type="button"
              :disabled="snapshotStore.discoveringDatabases"
              @click="snapshotStore.loadMariaDBDatabases()"
            >
              Discover databases
            </button>
          </div>
        </form>
      </section>

      <section class="table-panel" aria-label="Snapshot history">
        <div v-if="snapshotStore.loading" class="notice">Loading snapshots...</div>
        <div v-else-if="!hasSnapshots" class="empty-state">
          No snapshots have been registered.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Snapshot</th>
              <th>Repository</th>
              <th>Engine</th>
              <th>Source</th>
              <th>Status</th>
              <th class="actions-column">Lifecycle</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="snapshot in snapshotStore.items" :key="snapshot.uuid">
              <td>
                <strong>{{ snapshot.uuid }}</strong>
                <span>{{ new Date(snapshot.created_at).toLocaleString() }}</span>
              </td>
              <td>{{ repositoryName(snapshot.repository_uuid) }}</td>
              <td>{{ snapshot.engine }}</td>
              <td>{{ snapshot.source }}</td>
              <td>
                <span :class="['status-pill', snapshot.status]">
                  {{ snapshot.status }}
                </span>
                <small v-if="snapshot.failure_message">
                  {{ snapshot.failure_message }}
                </small>
              </td>
              <td class="row-actions">
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="
                    snapshot.status !== 'pending' ||
                    snapshotStore.transitioningUuid === snapshot.uuid
                  "
                  @click="snapshotStore.startSnapshot(snapshot.uuid)"
                >
                  Start
                </button>
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="
                    snapshot.status !== 'running' ||
                    snapshotStore.transitioningUuid === snapshot.uuid
                  "
                  @click="snapshotStore.completeSnapshot(snapshot.uuid)"
                >
                  Complete
                </button>
                <button
                  class="danger-button"
                  type="button"
                  :disabled="
                    snapshot.status === 'completed' ||
                    snapshotStore.transitioningUuid === snapshot.uuid
                  "
                  @click="snapshotStore.failSnapshot(snapshot.uuid)"
                >
                  Fail
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <header id="restores" class="page-header">
        <div>
          <p class="eyebrow">Milestone 7</p>
          <h2>Restores</h2>
        </div>
        <button class="secondary-button" type="button" @click="restoreStore.loadRestores()">
          Refresh
        </button>
      </header>

      <div v-if="restoreStore.error" class="notice error">
        {{ restoreStore.error }}
      </div>

      <section class="form-panel" aria-label="Restore form">
        <form class="restore-form" @submit.prevent="createRestore">
          <label>
            <span>Snapshot</span>
            <select v-model="restoreForm.snapshotUuid" required>
              <option disabled value="">Select completed snapshot</option>
              <option
                v-for="snapshot in completedSnapshots"
                :key="snapshot.uuid"
                :value="snapshot.uuid"
              >
                {{ snapshot.engine }} - {{ snapshot.source }}
              </option>
            </select>
          </label>
          <label>
            <span>Target path</span>
            <input v-model="restoreForm.targetPath" required placeholder="/restore/target" />
          </label>
          <div class="form-actions">
            <button
              class="primary-button"
              type="submit"
              :disabled="restoreStore.saving || completedSnapshots.length === 0"
            >
              Restore snapshot
            </button>
          </div>
        </form>
      </section>

      <section class="table-panel" aria-label="Restore history">
        <div v-if="restoreStore.loading" class="notice">Loading restore jobs...</div>
        <div v-else-if="!hasRestores" class="empty-state">
          No restore jobs have been requested.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Restore</th>
              <th>Snapshot</th>
              <th>Target</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Completed</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="restore in restoreStore.items" :key="restore.uuid">
              <td>
                <strong>{{ restore.uuid }}</strong>
                <span>{{ new Date(restore.created_at).toLocaleString() }}</span>
              </td>
              <td>
                {{ snapshotLabel(restore.snapshot_uuid) }}
                <span>{{ restore.snapshot_uuid }}</span>
              </td>
              <td>{{ restore.target_path }}</td>
              <td>
                <span :class="['status-pill', restore.status]">
                  {{ restore.status }}
                </span>
                <small v-if="restore.verification_message">
                  {{ restore.verification_message }}
                </small>
                <small v-if="restore.error_message">
                  {{ restore.error_message }}
                </small>
              </td>
              <td>
                <progress max="100" :value="restore.progress_percent" />
                <span>{{ restore.progress_percent }}%</span>
              </td>
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

      <header id="verification" class="page-header">
        <div>
          <p class="eyebrow">Milestone 8</p>
          <h2>Verification</h2>
        </div>
        <button
          class="secondary-button"
          type="button"
          @click="verificationStore.loadReports()"
        >
          Refresh
        </button>
      </header>

      <div v-if="verificationStore.error" class="notice error">
        {{ verificationStore.error }}
      </div>

      <section class="table-panel" aria-label="Repository verification">
        <div v-if="!hasRepositories" class="empty-state">
          No repositories are available for verification.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Repository</th>
              <th>Status</th>
              <th>Last validation</th>
              <th class="actions-column">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="repository in repositoryStore.items" :key="repository.uuid">
              <td>
                <strong>{{ repository.name }}</strong>
                <span>{{ repository.path }}</span>
              </td>
              <td>
                <span :class="['status-pill', repository.status]">
                  {{ repository.status }}
                </span>
                <small v-if="repository.validation_message">
                  {{ repository.validation_message }}
                </small>
              </td>
              <td>
                {{
                  repository.last_validated_at
                    ? new Date(repository.last_validated_at).toLocaleString()
                    : 'Not validated'
                }}
              </td>
              <td class="row-actions">
                <button
                  class="primary-button"
                  type="button"
                  :disabled="verificationStore.runningUuid === repository.uuid"
                  @click="verificationStore.verifyRepository(repository.uuid)"
                >
                  Verify integrity
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="table-panel" aria-label="Snapshot verification">
        <div v-if="completedSnapshots.length === 0" class="empty-state">
          No completed snapshots are available for verification.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Snapshot</th>
              <th>Repository</th>
              <th>Engine</th>
              <th>Source</th>
              <th class="actions-column">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="snapshot in completedSnapshots" :key="snapshot.uuid">
              <td>
                <strong>{{ snapshot.uuid }}</strong>
                <span>{{ new Date(snapshot.created_at).toLocaleString() }}</span>
              </td>
              <td>{{ repositoryName(snapshot.repository_uuid) }}</td>
              <td>{{ snapshot.engine }}</td>
              <td>{{ snapshot.source }}</td>
              <td class="row-actions">
                <button
                  class="primary-button"
                  type="button"
                  :disabled="verificationStore.runningUuid === snapshot.uuid"
                  @click="verificationStore.verifySnapshot(snapshot.uuid)"
                >
                  Verify snapshot
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="table-panel" aria-label="Verification reports">
        <div v-if="verificationStore.loading" class="notice">
          Loading verification reports...
        </div>
        <div v-else-if="verificationStore.reports.length === 0" class="empty-state">
          No verification reports have been generated.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Report</th>
              <th>Scope</th>
              <th>Repository</th>
              <th>Status</th>
              <th>Checks</th>
              <th>Generated</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in verificationStore.reports" :key="report.uuid">
              <td>
                <strong>{{ report.uuid }}</strong>
                <span v-if="report.snapshot_uuid">{{ report.snapshot_uuid }}</span>
              </td>
              <td>{{ report.scope }}</td>
              <td>{{ repositoryName(report.repository_uuid) }}</td>
              <td>
                <span :class="['status-pill', report.status]">
                  {{ report.status }}
                </span>
                <small>{{ report.message }}</small>
              </td>
              <td>{{ report.checked_count }} checked / {{ report.failed_count }} failed</td>
              <td>{{ new Date(report.created_at).toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <header id="notifications" class="page-header">
        <div>
          <p class="eyebrow">Milestone 10</p>
          <h2>Notifications</h2>
        </div>
        <button
          class="secondary-button"
          type="button"
          @click="notificationStore.loadNotifications()"
        >
          Refresh
        </button>
      </header>

      <div v-if="notificationStore.error" class="notice error">
        {{ notificationStore.error }}
      </div>

      <section class="form-panel" aria-label="Notification channel form">
        <form class="notification-form" @submit.prevent="saveNotification">
          <label>
            <span>Name</span>
            <input v-model="notificationForm.name" required maxlength="120" />
          </label>
          <label>
            <span>Driver</span>
            <select
              v-model="notificationForm.driver"
              :disabled="editingNotificationUuid !== null"
            >
              <option value="ntfy">ntfy</option>
              <option value="webhook">Webhook</option>
              <option value="email">Email</option>
            </select>
          </label>
          <label v-if="notificationForm.driver === 'ntfy'">
            <span>Server URL</span>
            <input
              v-model="notificationForm.serverUrl"
              required
              placeholder="https://ntfy.example.com"
            />
          </label>
          <label v-if="notificationForm.driver === 'ntfy'">
            <span>Topic</span>
            <input v-model="notificationForm.topic" required />
          </label>
          <label v-if="notificationForm.driver === 'webhook'">
            <span>Webhook URL</span>
            <input v-model="notificationForm.url" required />
          </label>
          <label v-if="notificationForm.driver === 'email'">
            <span>Recipient</span>
            <input v-model="notificationForm.recipient" required type="email" />
          </label>
          <label v-if="notificationForm.driver !== 'email'">
            <span>Token</span>
            <input v-model="notificationForm.token" type="password" />
          </label>
          <label class="checkbox-label">
            <input v-model="notificationForm.enabled" type="checkbox" />
            <span>Enabled</span>
          </label>
          <div class="form-actions">
            <button
              class="primary-button"
              type="submit"
              :disabled="notificationStore.saving"
            >
              {{ editingNotificationUuid ? 'Save channel' : 'Create channel' }}
            </button>
            <button
              v-if="editingNotificationUuid"
              class="secondary-button"
              type="button"
              @click="resetNotificationForm"
            >
              Cancel
            </button>
          </div>
        </form>
      </section>

      <section class="table-panel" aria-label="Notification channels">
        <div v-if="notificationStore.loading" class="notice">
          Loading notification channels...
        </div>
        <div v-else-if="notificationStore.channels.length === 0" class="empty-state">
          No notification channels have been configured.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Channel</th>
              <th>Driver</th>
              <th>Status</th>
              <th>Target</th>
              <th class="actions-column">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="channel in notificationStore.channels" :key="channel.uuid">
              <td>
                <strong>{{ channel.name }}</strong>
                <span>{{ channel.uuid }}</span>
              </td>
              <td>{{ channel.driver }}</td>
              <td>
                <span :class="['status-pill', channel.enabled ? 'enabled' : 'disabled']">
                  {{ channel.enabled ? 'enabled' : 'disabled' }}
                </span>
              </td>
              <td>
                {{
                  channel.driver === 'ntfy'
                    ? `${channel.config.server_url}/${channel.config.topic}`
                    : channel.driver === 'webhook'
                      ? channel.config.url
                      : channel.config.recipient
                }}
              </td>
              <td class="row-actions">
                <button
                  class="secondary-button"
                  type="button"
                  @click="editNotification(channel)"
                >
                  Edit
                </button>
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="notificationStore.testingUuid === channel.uuid"
                  @click="notificationStore.testChannel(channel.uuid)"
                >
                  Test
                </button>
                <button
                  class="danger-button"
                  type="button"
                  @click="notificationStore.deleteChannel(channel.uuid)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="table-panel" aria-label="Notification deliveries">
        <div v-if="notificationStore.deliveries.length === 0" class="empty-state">
          No notification deliveries have been recorded.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Delivery</th>
              <th>Channel</th>
              <th>Event</th>
              <th>Status</th>
              <th>Sent</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="delivery in notificationStore.deliveries" :key="delivery.uuid">
              <td>
                <strong>{{ delivery.title }}</strong>
                <span>{{ delivery.uuid }}</span>
              </td>
              <td>{{ delivery.channel_name }}</td>
              <td>{{ delivery.event_type }}</td>
              <td>
                <span :class="['status-pill', delivery.status]">
                  {{ delivery.status }}
                </span>
                <small v-if="delivery.error_message">
                  {{ delivery.error_message }}
                </small>
              </td>
              <td>
                {{
                  delivery.sent_at
                    ? new Date(delivery.sent_at).toLocaleString()
                    : new Date(delivery.created_at).toLocaleString()
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <header id="scheduler" class="page-header">
        <div>
          <p class="eyebrow">Milestone 6</p>
          <h2>Scheduler</h2>
        </div>
        <div class="form-actions">
          <button
            class="secondary-button"
            type="button"
            @click="schedulerStore.loadScheduler()"
          >
            Refresh
          </button>
          <button class="primary-button" type="button" @click="schedulerStore.runWorker()">
            Run worker
          </button>
        </div>
      </header>

      <div v-if="schedulerStore.error" class="notice error">
        {{ schedulerStore.error }}
      </div>

      <section class="form-panel" aria-label="Schedule form">
        <form class="scheduler-form" @submit.prevent="createPolicy">
          <label>
            <span>Name</span>
            <input v-model="policyForm.name" required maxlength="120" />
          </label>
          <label>
            <span>Repository</span>
            <select v-model="policyForm.repositoryUuid" required>
              <option disabled value="">Select repository</option>
              <option
                v-for="repository in repositoryStore.items"
                :key="repository.uuid"
                :value="repository.uuid"
              >
                {{ repository.name }}
              </option>
            </select>
          </label>
          <label>
            <span>Engine</span>
            <select v-model="policyForm.engine">
              <option value="filesystem">Filesystem</option>
              <option value="mariadb">MariaDB</option>
            </select>
          </label>
          <label>
            <span>Source</span>
            <input v-model="policyForm.source" required />
          </label>
          <label>
            <span>Every minutes</span>
            <input v-model.number="policyForm.intervalMinutes" min="1" type="number" />
          </label>
          <label>
            <span>Next run</span>
            <input v-model="policyForm.nextRunAt" required type="datetime-local" />
          </label>
          <label>
            <span>Retries</span>
            <input v-model.number="policyForm.maxRetries" min="0" max="10" type="number" />
          </label>
          <div class="form-actions">
            <button
              class="primary-button"
              type="submit"
              :disabled="schedulerStore.saving || !hasRepositories"
            >
              Create schedule
            </button>
          </div>
        </form>
      </section>

      <section class="table-panel" aria-label="Schedule policies">
        <div v-if="schedulerStore.loading" class="notice">Loading schedules...</div>
        <div v-else-if="schedulerStore.policies.length === 0" class="empty-state">
          No schedules have been created.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Name</th>
              <th>Repository</th>
              <th>Engine</th>
              <th>Source</th>
              <th>Next run</th>
              <th class="actions-column">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="policy in schedulerStore.policies" :key="policy.uuid">
              <td>
                <strong>{{ policy.name }}</strong>
                <span>{{ policy.uuid }}</span>
              </td>
              <td>{{ repositoryName(policy.repository_uuid) }}</td>
              <td>{{ policy.engine }}</td>
              <td>{{ policy.source }}</td>
              <td>{{ new Date(policy.next_run_at).toLocaleString() }}</td>
              <td class="row-actions">
                <button
                  class="secondary-button"
                  type="button"
                  @click="schedulerStore.enqueuePolicy(policy.uuid)"
                >
                  Enqueue
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="table-panel" aria-label="Backup jobs">
        <div v-if="schedulerStore.jobs.length === 0" class="empty-state">
          No backup jobs have been queued.
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>Job</th>
              <th>Policy</th>
              <th>Status</th>
              <th>Attempts</th>
              <th>Snapshot</th>
              <th>Completed</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in schedulerStore.jobs" :key="job.uuid">
              <td>
                <strong>{{ job.uuid }}</strong>
                <span>{{ new Date(job.queued_at).toLocaleString() }}</span>
              </td>
              <td>{{ job.policy_uuid }}</td>
              <td>
                <span :class="['status-pill', job.status]">
                  {{ job.status }}
                </span>
                <small v-if="job.error_message">{{ job.error_message }}</small>
              </td>
              <td>{{ job.attempts }} / {{ job.max_attempts }}</td>
              <td>{{ job.snapshot_uuid ?? 'None' }}</td>
              <td>
                {{
                  job.completed_at
                    ? new Date(job.completed_at).toLocaleString()
                    : 'Not completed'
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>
  </main>
</template>
