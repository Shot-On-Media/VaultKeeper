import { defineStore } from 'pinia'

import api from '../api'

export type StorageStatus = 'unknown' | 'valid' | 'invalid'

export interface StorageLocation {
  uuid: string
  name: string
  driver: 'local_filesystem'
  config: {
    path: string
  }
  status: StorageStatus
  last_validated_at: string | null
  validation_message: string | null
  created_at: string
  updated_at: string
}

export interface StorageForm {
  name: string
  path: string
}

interface StorageState {
  items: StorageLocation[]
  loading: boolean
  saving: boolean
  validatingUuid: string | null
  error: string | null
}

export const useStorageStore = defineStore('storage', {
  state: (): StorageState => ({
    items: [],
    loading: false,
    saving: false,
    validatingUuid: null,
    error: null,
  }),
  actions: {
    async loadStorage(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const response = await api.get<StorageLocation[]>('/storage')
        this.items = response.data
      } catch (error) {
        this.error = 'Storage locations could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async createStorage(form: StorageForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<StorageLocation>('/storage', {
          name: form.name,
          driver: 'local_filesystem',
          config: { path: form.path },
        })
        this.items = [...this.items, response.data].sort((left, right) =>
          left.name.localeCompare(right.name),
        )
      } catch (error) {
        this.error = 'Storage location could not be created.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async updateStorage(storageUuid: string, form: StorageForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.put<StorageLocation>(`/storage/${storageUuid}`, {
          name: form.name,
          config: { path: form.path },
        })
        this.items = this.items
          .map((item) => (item.uuid === storageUuid ? response.data : item))
          .sort((left, right) => left.name.localeCompare(right.name))
      } catch (error) {
        this.error = 'Storage location could not be updated.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async deleteStorage(storageUuid: string): Promise<void> {
      this.error = null
      try {
        await api.delete(`/storage/${storageUuid}`)
        this.items = this.items.filter((item) => item.uuid !== storageUuid)
      } catch (error) {
        this.error = 'Storage location could not be deleted.'
        throw error
      }
    },
    async validateStorage(storageUuid: string): Promise<void> {
      this.validatingUuid = storageUuid
      this.error = null
      try {
        await api.post(`/storage/${storageUuid}/validate`)
        await this.loadStorage()
      } catch (error) {
        this.error = 'Storage location could not be validated.'
        throw error
      } finally {
        this.validatingUuid = null
      }
    },
  },
})
