<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { RepositoryLocation, useRepositoryStore } from '../stores/repository'
import { useSchedulerStore } from '../stores/scheduler'
import { useSnapshotStore } from '../stores/snapshot'
import { StorageLocation, useStorageStore } from '../stores/storage'

const storageStore = useStorageStore()
const repositoryStore = useRepositoryStore()
const schedulerStore = useSchedulerStore()
const snapshotStore = useSnapshotStore()
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
const runningJobCount = computed(
  () => schedulerStore.jobs.filter((item) => item.status === 'running').length,
)

onMounted(() => {
  void storageStore.loadStorage()
  void repositoryStore.loadRepositories()
  void snapshotStore.loadSnapshots()
  void snapshotStore.loadMariaDBDatabases()
  void schedulerStore.loadScheduler()
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
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">VaultKeeper</p>
        <h1>Storage</h1>
      </div>
      <nav class="nav-list" aria-label="Primary">
        <a class="nav-item active" href="#storage">Storage</a>
        <a class="nav-item" href="#repositories">Repositories</a>
        <a class="nav-item" href="#snapshots">Snapshots</a>
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
