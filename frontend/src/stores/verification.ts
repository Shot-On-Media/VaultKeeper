import { defineStore } from 'pinia'

import api from '../api'

export type VerificationScope = 'repository' | 'snapshot'
export type VerificationStatus = 'passed' | 'failed' | 'warning'

export interface VerificationReport {
  uuid: string
  repository_uuid: string
  snapshot_uuid: string | null
  scope: VerificationScope
  status: VerificationStatus
  checked_count: number
  failed_count: number
  message: string
  details: Record<string, unknown>
  created_at: string
  updated_at: string
}

interface VerificationState {
  reports: VerificationReport[]
  loading: boolean
  runningUuid: string | null
  error: string | null
}

export const useVerificationStore = defineStore('verification', {
  state: (): VerificationState => ({
    reports: [],
    loading: false,
    runningUuid: null,
    error: null,
  }),
  actions: {
    async loadReports(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const response = await api.get<VerificationReport[]>('/verification/reports')
        this.reports = response.data
      } catch (error) {
        this.error = 'Verification reports could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async verifyRepository(repositoryUuid: string): Promise<void> {
      await this.runVerification(
        repositoryUuid,
        `/verification/repositories/${repositoryUuid}`,
      )
    },
    async verifySnapshot(snapshotUuid: string): Promise<void> {
      await this.runVerification(snapshotUuid, `/verification/snapshots/${snapshotUuid}`)
    },
    async runVerification(targetUuid: string, endpoint: string): Promise<void> {
      this.runningUuid = targetUuid
      this.error = null
      try {
        const response = await api.post<VerificationReport>(endpoint)
        this.reports = [response.data, ...this.reports]
      } catch (error) {
        this.error = 'Verification could not be completed.'
        throw error
      } finally {
        this.runningUuid = null
      }
    },
  },
})
