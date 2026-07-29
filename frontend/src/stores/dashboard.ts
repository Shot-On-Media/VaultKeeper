import { defineStore } from 'pinia'

import api from '../api'

export interface DashboardMetric {
  total: number
  healthy: number
  warning: number
  failed: number
}

export interface DashboardSnapshotMetrics {
  total: number
  completed: number
  running: number
  failed: number
  total_bytes: number
}

export interface DashboardJobMetrics {
  running: number
  failed: number
  queued: number
  retrying: number
}

export interface DashboardRestoreMetrics {
  total: number
  completed: number
  running: number
  failed: number
}

export interface DashboardVerificationMetrics {
  total: number
  passed: number
  warning: number
  failed: number
}

export interface DashboardRecentRestore {
  uuid: string
  snapshot_uuid: string
  status: string
  target_path: string
  completed_at: string | null
  created_at: string
}

export interface DashboardSummary {
  storage: DashboardMetric
  repositories: DashboardMetric
  snapshots: DashboardSnapshotMetrics
  jobs: DashboardJobMetrics
  restores: DashboardRestoreMetrics
  verification: DashboardVerificationMetrics
  recent_restores: DashboardRecentRestore[]
}

interface DashboardState {
  summary: DashboardSummary | null
  loading: boolean
  error: string | null
}

export const useDashboardStore = defineStore('dashboard', {
  state: (): DashboardState => ({
    summary: null,
    loading: false,
    error: null,
  }),
  actions: {
    async loadDashboard(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const response = await api.get<DashboardSummary>('/dashboard')
        this.summary = response.data
      } catch (error) {
        this.error = 'Dashboard could not be loaded.'
      } finally {
        this.loading = false
      }
    },
  },
})
