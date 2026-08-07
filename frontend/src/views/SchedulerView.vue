<script setup lang="ts">
import { onMounted, reactive } from 'vue'

import { useRepositoryStore } from '../stores/repository'
import { useSchedulerStore } from '../stores/scheduler'

const repositoryStore = useRepositoryStore()
const schedulerStore = useSchedulerStore()

const policyForm = reactive({
  name: '',
  repositoryUuid: '',
  engine: 'filesystem' as const,
  source: '',
  intervalMinutes: 60,
  nextRunAt: new Date(Date.now() + 60000).toISOString().slice(0, 16),
  maxRetries: 2,
})

onMounted(() => {
  void repositoryStore.loadRepositories()
  void schedulerStore.loadScheduler()
})

function repositoryName(repositoryUuid: string): string {
  return (
    repositoryStore.items.find((repository) => repository.uuid === repositoryUuid)?.name ??
    repositoryUuid
  )
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
  <header class="page-header">
    <div>
      <p class="eyebrow">Automation</p>
      <h2>Scheduler</h2>
    </div>
    <div class="form-actions">
      <button class="secondary-button" type="button" @click="schedulerStore.loadScheduler()">
        Refresh
      </button>
      <button class="primary-button" type="button" @click="schedulerStore.runWorker()">
        Run worker
      </button>
    </div>
  </header>

  <div v-if="schedulerStore.error" class="notice error">{{ schedulerStore.error }}</div>

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
        <button class="primary-button" type="submit" :disabled="schedulerStore.saving">
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
            <span :class="['status-pill', job.status]">{{ job.status }}</span>
            <small v-if="job.error_message">{{ job.error_message }}</small>
          </td>
          <td>{{ job.attempts }} / {{ job.max_attempts }}</td>
          <td>{{ job.snapshot_uuid ?? 'None' }}</td>
          <td>
            {{
              job.completed_at ? new Date(job.completed_at).toLocaleString() : 'Not completed'
            }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
