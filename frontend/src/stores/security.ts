import { defineStore } from 'pinia'

import api from '../api'

export interface APIKeyRecord {
  uuid: string
  name: string
  key_prefix: string
  enabled: boolean
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface AuditLogRecord {
  uuid: string
  actor: string
  action: string
  path: string
  method: string
  status_code: number
  client_host: string | null
  message: string | null
  created_at: string
  updated_at: string
}

interface SecurityState {
  accessToken: string
  tokenExpiresAt: string | null
  apiKeys: APIKeyRecord[]
  auditLogs: AuditLogRecord[]
  latestSecret: string | null
  loading: boolean
  saving: boolean
  error: string | null
}

export const useSecurityStore = defineStore('security', {
  state: (): SecurityState => ({
    accessToken: window.localStorage.getItem('vaultkeeper.accessToken') ?? '',
    tokenExpiresAt: window.localStorage.getItem('vaultkeeper.tokenExpiresAt'),
    apiKeys: [],
    auditLogs: [],
    latestSecret: null,
    loading: false,
    saving: false,
    error: null,
  }),
  getters: {
    isAuthenticated: (state) => state.accessToken.length > 0,
  },
  actions: {
    async login(username: string, password: string): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<{
          access_token: string
          expires_at: string
        }>('/auth/login', { username, password })
        this.accessToken = response.data.access_token
        this.tokenExpiresAt = response.data.expires_at
        window.localStorage.setItem('vaultkeeper.accessToken', this.accessToken)
        window.localStorage.setItem('vaultkeeper.tokenExpiresAt', this.tokenExpiresAt)
      } catch (error) {
        this.error = 'Login failed.'
        throw error
      } finally {
        this.saving = false
      }
    },
    logout(): void {
      this.accessToken = ''
      this.tokenExpiresAt = null
      this.apiKeys = []
      this.auditLogs = []
      this.latestSecret = null
      window.localStorage.removeItem('vaultkeeper.accessToken')
      window.localStorage.removeItem('vaultkeeper.tokenExpiresAt')
    },
    async loadSecurity(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const [keysResponse, auditResponse] = await Promise.all([
          api.get<APIKeyRecord[]>('/security/api-keys'),
          api.get<AuditLogRecord[]>('/security/audit-logs'),
        ])
        this.apiKeys = keysResponse.data
        this.auditLogs = auditResponse.data
      } catch (error) {
        this.error = 'Security records could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async createAPIKey(name: string): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<APIKeyRecord & { secret: string }>(
          '/security/api-keys',
          { name },
        )
        const { secret, ...apiKey } = response.data
        this.latestSecret = secret
        this.apiKeys = [...this.apiKeys, apiKey].sort((left, right) =>
          left.name.localeCompare(right.name),
        )
      } catch (error) {
        this.error = 'API key could not be created.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async setAPIKeyEnabled(apiKeyUuid: string, enabled: boolean): Promise<void> {
      this.error = null
      try {
        const apiKey = this.apiKeys.find((item) => item.uuid === apiKeyUuid)
        const response = await api.put<APIKeyRecord>(
          `/security/api-keys/${apiKeyUuid}`,
          { name: apiKey?.name, enabled },
        )
        this.apiKeys = this.apiKeys.map((item) =>
          item.uuid === apiKeyUuid ? response.data : item,
        )
      } catch (error) {
        this.error = 'API key could not be updated.'
        throw error
      }
    },
    async deleteAPIKey(apiKeyUuid: string): Promise<void> {
      this.error = null
      try {
        await api.delete(`/security/api-keys/${apiKeyUuid}`)
        this.apiKeys = this.apiKeys.filter((item) => item.uuid !== apiKeyUuid)
      } catch (error) {
        this.error = 'API key could not be deleted.'
        throw error
      }
    },
  },
})
