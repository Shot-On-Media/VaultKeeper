<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { StorageLocation, useStorageStore } from '../stores/storage'

const storageStore = useStorageStore()
const editingUuid = ref<string | null>(null)
const form = reactive({
  name: '',
  path: '',
})

const hasStorage = computed(() => storageStore.items.length > 0)
const validCount = computed(
  () => storageStore.items.filter((item) => item.status === 'valid').length,
)
const invalidCount = computed(
  () => storageStore.items.filter((item) => item.status === 'invalid').length,
)

onMounted(() => {
  void storageStore.loadStorage()
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
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">VaultKeeper</p>
        <h1>Storage</h1>
      </div>
      <nav class="nav-list" aria-label="Primary">
        <a class="nav-item active" href="/">Storage</a>
      </nav>
      <dl class="summary-list">
        <div>
          <dt>Total</dt>
          <dd>{{ storageStore.items.length }}</dd>
        </div>
        <div>
          <dt>Valid</dt>
          <dd>{{ validCount }}</dd>
        </div>
        <div>
          <dt>Invalid</dt>
          <dd>{{ invalidCount }}</dd>
        </div>
      </dl>
    </aside>

    <section class="workspace">
      <header class="page-header">
        <div>
          <p class="eyebrow">Milestone 1</p>
          <h2>Storage Locations</h2>
        </div>
        <button class="secondary-button" type="button" @click="storageStore.loadStorage">
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
    </section>
  </main>
</template>
