import { defineStore } from 'pinia'

import api from '../api'

export type BackupEngine = 'filesystem' | 'mariadb'
export type BackupJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'retrying'

export interface BackupPolicy {
  uuid: string
  repository_uuid: string
  name: string
  engine: BackupEngine
  source: string
  interval_minutes: number
  enabled: boolean
  next_run_at: string
  max_retries: number
  created_at: string
  updated_at: string
}

export interface BackupJob {
  uuid: string
  policy_uuid: string
  status: BackupJobStatus
  attempts: number
  max_attempts: number
  queued_at: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  snapshot_uuid: string | null
  created_at: string
  updated_at: string
}

export interface BackupPolicyForm {
  name: string
  repositoryUuid: string
  engine: BackupEngine
  source: string
  intervalMinutes: number
  nextRunAt: string
  maxRetries: number
}

interface SchedulerState {
  policies: BackupPolicy[]
  jobs: BackupJob[]
  loading: boolean
  saving: boolean
  error: string | null
}

export const useSchedulerStore = defineStore('scheduler', {
  state: (): SchedulerState => ({
    policies: [],
    jobs: [],
    loading: false,
    saving: false,
    error: null,
  }),
  actions: {
    async loadScheduler(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const [policiesResponse, jobsResponse] = await Promise.all([
          api.get<BackupPolicy[]>('/scheduler/policies'),
          api.get<BackupJob[]>('/scheduler/jobs'),
        ])
        this.policies = policiesResponse.data
        this.jobs = jobsResponse.data
      } catch (error) {
        this.error = 'Scheduler state could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async createPolicy(form: BackupPolicyForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<BackupPolicy>('/scheduler/policies', {
          name: form.name,
          repository_uuid: form.repositoryUuid,
          engine: form.engine,
          source: form.source,
          interval_minutes: form.intervalMinutes,
          enabled: true,
          next_run_at: new Date(form.nextRunAt).toISOString(),
          max_retries: form.maxRetries,
        })
        this.policies = [...this.policies, response.data].sort((left, right) =>
          left.name.localeCompare(right.name),
        )
      } catch (error) {
        this.error = 'Schedule could not be created.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async enqueuePolicy(policyUuid: string): Promise<void> {
      this.error = null
      try {
        const response = await api.post<BackupJob>(
          `/scheduler/policies/${policyUuid}/enqueue`,
        )
        this.jobs = [response.data, ...this.jobs]
      } catch (error) {
        this.error = 'Schedule could not be enqueued.'
        throw error
      }
    },
    async runWorker(): Promise<void> {
      this.error = null
      try {
        await api.post('/scheduler/work')
        await this.loadScheduler()
      } catch (error) {
        this.error = 'Worker could not process a job.'
        throw error
      }
    },
  },
})
