<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'

import { useRestoreStore } from '../stores/restore'
import { useSnapshotStore } from '../stores/snapshot'

const restoreStore = useRestoreStore()
const snapshotStore = useSnapshotStore()

const restoreForm = reactive({
  snapshotUuid: '',
  targetPath: '',
})

const completedSnapshots = computed(() =>
  snapshotStore.items.filter((item) => item.status === 'completed'),
)

onMounted(() => {
  void snapshotStore.loadSnapshots()
  void restoreStore.loadRestores()
})

function snapshotLabel(snapshotUuid: string): string {
  const snapshot = snapshotStore.items.find((item) => item.uuid === snapshotUuid)
  if (snapshot === undefined) {
    return snapshotUuid
  }
  return `${snapshot.engine} - ${snapshot.source}`
}

async function createRestore(): Promise<void> {
  await restoreStore.createRestore(restoreForm)
  restoreForm.snapshotUuid = ''
  restoreForm.targetPath = ''
}
</script>

<template>
  <header class="page-header">
    <div>
      <p class="eyebrow">Recovery</p>
      <h2>Restore Snapshots</h2>
    </div>
    <button class="secondary-button" type="button" @click="restoreStore.loadRestores()">
      Refresh
    </button>
  </header>

  <div v-if="restoreStore.error" class="notice error">{{ restoreStore.error }}</div>

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
    <div v-else-if="restoreStore.items.length === 0" class="empty-state">
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
            <span :class="['status-pill', restore.status]">{{ restore.status }}</span>
            <small v-if="restore.verification_message">
              {{ restore.verification_message }}
            </small>
            <small v-if="restore.error_message">{{ restore.error_message }}</small>
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
</template>
