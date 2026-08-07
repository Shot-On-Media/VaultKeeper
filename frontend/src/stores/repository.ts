import { defineStore } from 'pinia'

import api from '../api'

export type RepositoryStatus = 'unknown' | 'valid' | 'invalid'

export interface RepositoryLocation {
  uuid: string
  storage_uuid: string
  name: string
  path: string
  status: RepositoryStatus
  last_validated_at: string | null
  validation_message: string | null
  created_at: string
  updated_at: string
}

export interface RepositoryForm {
  name: string
  storageUuid: string
}

interface RepositoryState {
  items: RepositoryLocation[]
  loading: boolean
  saving: boolean
  validatingUuid: string | null
  error: string | null
}

export const useRepositoryStore = defineStore('repository', {
  state: (): RepositoryState => ({
    items: [],
    loading: false,
    saving: false,
    validatingUuid: null,
    error: null,
  }),
  actions: {
    async loadRepositories(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const response = await api.get<RepositoryLocation[]>('/repositories')
        this.items = response.data
      } catch (error) {
        this.error = 'Repositories could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async createRepository(form: RepositoryForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<RepositoryLocation>('/repositories', {
          name: form.name,
          storage_uuid: form.storageUuid,
        })
        this.items = [...this.items, response.data].sort((left, right) =>
          left.name.localeCompare(right.name),
        )
      } catch (error) {
        this.error = 'Repository could not be created.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async updateRepository(repositoryUuid: string, name: string): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.put<RepositoryLocation>(
          `/repositories/${repositoryUuid}`,
          { name },
        )
        this.items = this.items
          .map((item) => (item.uuid === repositoryUuid ? response.data : item))
          .sort((left, right) => left.name.localeCompare(right.name))
      } catch (error) {
        this.error = 'Repository could not be updated.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async deleteRepository(repositoryUuid: string): Promise<void> {
      this.error = null
      try {
        await api.delete(`/repositories/${repositoryUuid}`)
        this.items = this.items.filter((item) => item.uuid !== repositoryUuid)
      } catch (error) {
        this.error = 'Repository could not be deleted.'
        throw error
      }
    },
    async validateRepository(repositoryUuid: string): Promise<void> {
      this.validatingUuid = repositoryUuid
      this.error = null
      try {
        await api.post(`/repositories/${repositoryUuid}/validate`)
        await this.loadRepositories()
      } catch (error) {
        this.error = 'Repository could not be validated.'
        throw error
      } finally {
        this.validatingUuid = null
      }
    },
  },
})
