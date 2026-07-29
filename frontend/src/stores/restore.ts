import { defineStore } from 'pinia'

import api from '../api'

export type RestoreStatus = 'requested' | 'running' | 'completed' | 'failed'

export interface RestoreJob {
  uuid: string
  snapshot_uuid: string
  status: RestoreStatus
  target_path: string
  progress_percent: number
  verification_message: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface RestoreForm {
  snapshotUuid: string
  targetPath: string
}

interface RestoreState {
  items: RestoreJob[]
  loading: boolean
  saving: boolean
  error: string | null
}

export const useRestoreStore = defineStore('restore', {
  state: (): RestoreState => ({
    items: [],
    loading: false,
    saving: false,
    error: null,
  }),
  actions: {
    async loadRestores(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const response = await api.get<RestoreJob[]>('/restores')
        this.items = response.data
      } catch (error) {
        this.error = 'Restore history could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async createRestore(form: RestoreForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<RestoreJob>('/restores', {
          snapshot_uuid: form.snapshotUuid,
          target_path: form.targetPath,
        })
        this.items = [response.data, ...this.items]
      } catch (error) {
        this.error = 'Snapshot could not be restored.'
        throw error
      } finally {
        this.saving = false
      }
    },
  },
})
