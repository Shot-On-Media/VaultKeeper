<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'

import { useRepositoryStore } from '../stores/repository'
import { useSnapshotStore } from '../stores/snapshot'

const repositoryStore = useRepositoryStore()
const snapshotStore = useSnapshotStore()

const snapshotForm = reactive({
  repositoryUuid: '',
  engine: 'framework',
  source: '',
})
const mariaDBForm = reactive({
  repositoryUuid: '',
  databaseName: '',
})

const completedSnapshots = computed(
  () => snapshotStore.items.filter((item) => item.status === 'completed').length,
)

onMounted(() => {
  void repositoryStore.loadRepositories()
  void snapshotStore.loadSnapshots()
  void snapshotStore.loadMariaDBDatabases()
})

function repositoryName(repositoryUuid: string): string {
  return (
    repositoryStore.items.find((repository) => repository.uuid === repositoryUuid)?.name ??
    repositoryUuid
  )
}

function resetSnapshotForm(): void {
  snapshotForm.repositoryUuid = ''
  snapshotForm.engine = 'framework'
  snapshotForm.source = ''
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
  mariaDBForm.repositoryUuid = ''
  mariaDBForm.databaseName = ''
}
</script>

<template>
  <header class="page-header">
    <div>
      <p class="eyebrow">Backups</p>
      <h2>Backup Engines</h2>
    </div>
    <button class="secondary-button" type="button" @click="snapshotStore.loadSnapshots()">
      Refresh
    </button>
  </header>

  <div v-if="snapshotStore.error" class="notice error">{{ snapshotStore.error }}</div>

  <section class="dashboard-grid">
    <article class="metric-card">
      <span class="status-pill completed">Completed</span>
      <strong>{{ completedSnapshots }}</strong>
      <span>{{ snapshotStore.items.length }} total snapshots</span>
    </article>
    <article class="metric-card">
      <span class="status-pill running">Running</span>
      <strong>{{ snapshotStore.items.filter((item) => item.status === 'running').length }}</strong>
      <span>Active snapshot jobs</span>
    </article>
    <article class="metric-card">
      <span class="status-pill failed">Failed</span>
      <strong>{{ snapshotStore.items.filter((item) => item.status === 'failed').length }}</strong>
      <span>Failed snapshots</span>
    </article>
  </section>

  <section class="form-panel" aria-label="Filesystem backup form">
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
        <button class="secondary-button" type="submit" :disabled="snapshotStore.saving">
          Register snapshot
        </button>
        <button
          class="primary-button"
          type="button"
          :disabled="snapshotStore.saving"
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
        <button class="primary-button" type="submit" :disabled="snapshotStore.saving">
          Run MariaDB backup
        </button>
      </div>
    </form>
  </section>

  <section class="table-panel" aria-label="Snapshot history">
    <div v-if="snapshotStore.loading" class="notice">Loading snapshots...</div>
    <div v-else-if="snapshotStore.items.length === 0" class="empty-state">
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
            <span :class="['status-pill', snapshot.status]">{{ snapshot.status }}</span>
            <small v-if="snapshot.failure_message">{{ snapshot.failure_message }}</small>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
