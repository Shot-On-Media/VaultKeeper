import { defineStore } from 'pinia'

import api from '../api'

export type SnapshotStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface SnapshotRecord {
  uuid: string
  repository_uuid: string
  engine: string
  source: string
  status: SnapshotStatus
  size_bytes: number | null
  manifest: Record<string, unknown>
  started_at: string | null
  completed_at: string | null
  failure_message: string | null
  created_at: string
  updated_at: string
}

export interface SnapshotForm {
  repositoryUuid: string
  engine: string
  source: string
}

export interface FilesystemBackupForm {
  repositoryUuid: string
  sourcePath: string
}

interface SnapshotState {
  items: SnapshotRecord[]
  loading: boolean
  saving: boolean
  transitioningUuid: string | null
  error: string | null
}

export const useSnapshotStore = defineStore('snapshot', {
  state: (): SnapshotState => ({
    items: [],
    loading: false,
    saving: false,
    transitioningUuid: null,
    error: null,
  }),
  actions: {
    async loadSnapshots(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const response = await api.get<SnapshotRecord[]>('/snapshots')
        this.items = response.data
      } catch (error) {
        this.error = 'Snapshots could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async registerSnapshot(form: SnapshotForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<SnapshotRecord>('/snapshots', {
          repository_uuid: form.repositoryUuid,
          engine: form.engine,
          source: form.source,
        })
        this.items = [response.data, ...this.items]
      } catch (error) {
        this.error = 'Snapshot could not be registered.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async runFilesystemBackup(form: FilesystemBackupForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<{ snapshot: SnapshotRecord }>(
          '/filesystem-backups',
          {
            repository_uuid: form.repositoryUuid,
            source_path: form.sourcePath,
          },
        )
        this.items = [response.data.snapshot, ...this.items]
      } catch (error) {
        this.error = 'Filesystem backup could not be completed.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async startSnapshot(snapshotUuid: string): Promise<void> {
      await this.transitionSnapshot(snapshotUuid, 'start')
    },
    async completeSnapshot(snapshotUuid: string): Promise<void> {
      await this.transitionSnapshot(snapshotUuid, 'complete', {
        size_bytes: 0,
        manifest: {},
      })
    },
    async failSnapshot(snapshotUuid: string): Promise<void> {
      await this.transitionSnapshot(snapshotUuid, 'fail', {
        failure_message: 'Marked failed by operator.',
      })
    },
    async transitionSnapshot(
      snapshotUuid: string,
      action: 'start' | 'complete' | 'fail',
      payload?: Record<string, unknown>,
    ): Promise<void> {
      this.transitioningUuid = snapshotUuid
      this.error = null
      try {
        const response = await api.post<SnapshotRecord>(
          `/snapshots/${snapshotUuid}/${action}`,
          payload,
        )
        this.items = this.items.map((item) =>
          item.uuid === snapshotUuid ? response.data : item,
        )
      } catch (error) {
        this.error = 'Snapshot status could not be updated.'
        throw error
      } finally {
        this.transitioningUuid = null
      }
    },
  },
})
