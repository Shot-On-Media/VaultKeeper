<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  NotificationChannel,
  NotificationDriver,
  useNotificationStore,
} from '../stores/notification'
import { RepositoryLocation, useRepositoryStore } from '../stores/repository'
import { useSecurityStore } from '../stores/security'
import { useSnapshotStore } from '../stores/snapshot'
import { StorageLocation, useStorageStore } from '../stores/storage'
import { useVerificationStore } from '../stores/verification'

const storageStore = useStorageStore()
const repositoryStore = useRepositoryStore()
const snapshotStore = useSnapshotStore()
const verificationStore = useVerificationStore()
const notificationStore = useNotificationStore()
const securityStore = useSecurityStore()

const editingStorageUuid = ref<string | null>(null)
const editingRepositoryUuid = ref<string | null>(null)
const editingNotificationUuid = ref<string | null>(null)

const storageForm = reactive({ name: '', path: '' })
const repositoryForm = reactive({ name: '', storageUuid: '' })
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
const loginForm = reactive({ username: 'admin', password: '' })
const apiKeyForm = reactive({ name: '' })

const completedSnapshots = computed(() =>
  snapshotStore.items.filter((item) => item.status === 'completed'),
)

onMounted(() => {
  void storageStore.loadStorage()
  void repositoryStore.loadRepositories()
  void snapshotStore.loadSnapshots()
  void verificationStore.loadReports()
  void notificationStore.loadNotifications()
  void securityStore.loadSecurity()
})

function storageName(storageUuid: string): string {
  return storageStore.items.find((storage) => storage.uuid === storageUuid)?.name ?? storageUuid
}

function repositoryName(repositoryUuid: string): string {
  return (
    repositoryStore.items.find((repository) => repository.uuid === repositoryUuid)?.name ??
    repositoryUuid
  )
}

function resetStorageForm(): void {
  editingStorageUuid.value = null
  storageForm.name = ''
  storageForm.path = ''
}

function editStorage(storage: StorageLocation): void {
  editingStorageUuid.value = storage.uuid
  storageForm.name = storage.name
  storageForm.path = storage.config.path
}

async function saveStorage(): Promise<void> {
  if (editingStorageUuid.value === null) {
    await storageStore.createStorage(storageForm)
  } else {
    await storageStore.updateStorage(editingStorageUuid.value, storageForm)
  }
  resetStorageForm()
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

async function login(): Promise<void> {
  await securityStore.login(loginForm.username, loginForm.password)
  loginForm.password = ''
  await securityStore.loadSecurity()
}

async function createAPIKey(): Promise<void> {
  await securityStore.createAPIKey(apiKeyForm.name)
  apiKeyForm.name = ''
}
</script>

<template>
  <header class="page-header">
    <div>
      <p class="eyebrow">Configuration</p>
      <h2>Settings</h2>
    </div>
    <button class="secondary-button" type="button" @click="verificationStore.loadReports()">
      Refresh
    </button>
  </header>

  <div v-if="storageStore.error" class="notice error">{{ storageStore.error }}</div>
  <div v-if="repositoryStore.error" class="notice error">{{ repositoryStore.error }}</div>
  <div v-if="verificationStore.error" class="notice error">{{ verificationStore.error }}</div>
  <div v-if="notificationStore.error" class="notice error">{{ notificationStore.error }}</div>
  <div v-if="securityStore.error" class="notice error">{{ securityStore.error }}</div>

  <section class="settings-grid">
    <section class="form-panel" aria-label="Storage form">
      <div class="section-heading"><h3>Storage</h3></div>
      <form class="storage-form" @submit.prevent="saveStorage">
        <label>
          <span>Name</span>
          <input v-model="storageForm.name" required maxlength="120" />
        </label>
        <label>
          <span>Local path</span>
          <input v-model="storageForm.path" required placeholder="/backups" />
        </label>
        <div class="form-actions">
          <button class="primary-button" type="submit" :disabled="storageStore.saving">
            {{ editingStorageUuid ? 'Save storage' : 'Create storage' }}
          </button>
          <button
            v-if="editingStorageUuid"
            class="secondary-button"
            type="button"
            @click="resetStorageForm"
          >
            Cancel
          </button>
        </div>
      </form>
    </section>

    <section class="form-panel" aria-label="Repository form">
      <div class="section-heading"><h3>Repositories</h3></div>
      <form class="repository-form" @submit.prevent="saveRepository">
        <label>
          <span>Name</span>
          <input v-model="repositoryForm.name" required maxlength="120" />
        </label>
        <label>
          <span>Storage</span>
          <select v-model="repositoryForm.storageUuid" required>
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
          <button class="primary-button" type="submit" :disabled="repositoryStore.saving">
            {{ editingRepositoryUuid ? 'Save repository' : 'Create repository' }}
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
  </section>

  <section class="table-panel" aria-label="Storage and repositories">
    <table>
      <thead>
        <tr>
          <th>Kind</th>
          <th>Name</th>
          <th>Location</th>
          <th>Status</th>
          <th class="actions-column">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="storage in storageStore.items" :key="storage.uuid">
          <td>Storage</td>
          <td>
            <strong>{{ storage.name }}</strong>
            <span>{{ storage.uuid }}</span>
          </td>
          <td>{{ storage.config.path }}</td>
          <td><span :class="['status-pill', storage.status]">{{ storage.status }}</span></td>
          <td class="row-actions">
            <button class="secondary-button" type="button" @click="editStorage(storage)">
              Edit
            </button>
            <button
              class="secondary-button"
              type="button"
              @click="storageStore.validateStorage(storage.uuid)"
            >
              Validate
            </button>
          </td>
        </tr>
        <tr v-for="repository in repositoryStore.items" :key="repository.uuid">
          <td>Repository</td>
          <td>
            <strong>{{ repository.name }}</strong>
            <span>{{ repository.uuid }}</span>
          </td>
          <td>{{ repository.path }}</td>
          <td>
            <span :class="['status-pill', repository.status]">{{ repository.status }}</span>
            <small>{{ storageName(repository.storage_uuid) }}</small>
          </td>
          <td class="row-actions">
            <button class="secondary-button" type="button" @click="editRepository(repository)">
              Edit
            </button>
            <button
              class="secondary-button"
              type="button"
              @click="repositoryStore.validateRepository(repository.uuid)"
            >
              Validate
            </button>
            <button
              class="primary-button"
              type="button"
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
    <div class="section-heading"><h3>Snapshot Verification</h3></div>
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
          <td>{{ snapshot.uuid }}</td>
          <td>{{ repositoryName(snapshot.repository_uuid) }}</td>
          <td>{{ snapshot.engine }}</td>
          <td>{{ snapshot.source }}</td>
          <td class="row-actions">
            <button
              class="primary-button"
              type="button"
              @click="verificationStore.verifySnapshot(snapshot.uuid)"
            >
              Verify snapshot
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="form-panel" aria-label="Notification channel form">
    <div class="section-heading"><h3>Notifications</h3></div>
    <form class="notification-form" @submit.prevent="saveNotification">
      <label>
        <span>Name</span>
        <input v-model="notificationForm.name" required maxlength="120" />
      </label>
      <label>
        <span>Driver</span>
        <select v-model="notificationForm.driver">
          <option value="ntfy">ntfy</option>
          <option value="webhook">Webhook</option>
          <option value="email">Email</option>
        </select>
      </label>
      <label v-if="notificationForm.driver === 'ntfy'">
        <span>Server URL</span>
        <input v-model="notificationForm.serverUrl" required />
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
        <button class="primary-button" type="submit" :disabled="notificationStore.saving">
          {{ editingNotificationUuid ? 'Save channel' : 'Create channel' }}
        </button>
      </div>
    </form>
  </section>

  <section class="table-panel" aria-label="Notification channels">
    <table>
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
          <td>{{ channel.config.topic ?? channel.config.url ?? channel.config.recipient }}</td>
          <td class="row-actions">
            <button class="secondary-button" type="button" @click="editNotification(channel)">
              Edit
            </button>
            <button
              class="secondary-button"
              type="button"
              @click="notificationStore.testChannel(channel.uuid)"
            >
              Test
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="form-panel" aria-label="Authentication form">
    <div class="section-heading"><h3>Security</h3></div>
    <form class="login-form" @submit.prevent="login">
      <label>
        <span>Username</span>
        <input v-model="loginForm.username" required autocomplete="username" />
      </label>
      <label>
        <span>Password</span>
        <input
          v-model="loginForm.password"
          required
          autocomplete="current-password"
          type="password"
        />
      </label>
      <div class="form-actions">
        <button class="primary-button" type="submit" :disabled="securityStore.saving">
          Login
        </button>
        <button class="secondary-button" type="button" @click="securityStore.logout()">
          Logout
        </button>
      </div>
    </form>
  </section>

  <section class="form-panel" aria-label="API key form">
    <form class="api-key-form" @submit.prevent="createAPIKey">
      <label>
        <span>API key name</span>
        <input v-model="apiKeyForm.name" required maxlength="120" />
      </label>
      <div class="form-actions">
        <button class="primary-button" type="submit" :disabled="securityStore.saving">
          Create API key
        </button>
      </div>
    </form>
    <div v-if="securityStore.latestSecret" class="secret-panel">
      <strong>New API key</strong>
      <code>{{ securityStore.latestSecret }}</code>
    </div>
  </section>

  <section class="table-panel" aria-label="Security records">
    <table>
      <thead>
        <tr>
          <th>API Key</th>
          <th>Status</th>
          <th>Last Used</th>
          <th class="actions-column">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="apiKey in securityStore.apiKeys" :key="apiKey.uuid">
          <td>
            <strong>{{ apiKey.name }}</strong>
            <span>{{ apiKey.key_prefix }}</span>
          </td>
          <td>
            <span :class="['status-pill', apiKey.enabled ? 'enabled' : 'disabled']">
              {{ apiKey.enabled ? 'enabled' : 'disabled' }}
            </span>
          </td>
          <td>
            {{ apiKey.last_used_at ? new Date(apiKey.last_used_at).toLocaleString() : 'Never' }}
          </td>
          <td class="row-actions">
            <button
              class="secondary-button"
              type="button"
              @click="securityStore.setAPIKeyEnabled(apiKey.uuid, !apiKey.enabled)"
            >
              {{ apiKey.enabled ? 'Disable' : 'Enable' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
