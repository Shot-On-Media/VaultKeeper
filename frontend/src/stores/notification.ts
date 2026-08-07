import { defineStore } from 'pinia'

import api from '../api'

export type NotificationDriver = 'email' | 'webhook' | 'ntfy'
export type NotificationDeliveryStatus = 'sent' | 'failed' | 'skipped'

export interface NotificationChannel {
  uuid: string
  name: string
  driver: NotificationDriver
  enabled: boolean
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface NotificationDelivery {
  uuid: string
  channel_uuid: string
  channel_name: string
  driver: NotificationDriver
  event_type: string
  status: NotificationDeliveryStatus
  title: string
  message: string
  response_code: number | null
  error_message: string | null
  sent_at: string | null
  created_at: string
  updated_at: string
}

export interface NotificationChannelForm {
  name: string
  driver: NotificationDriver
  enabled: boolean
  serverUrl: string
  topic: string
  token: string
  url: string
  recipient: string
}

interface NotificationState {
  channels: NotificationChannel[]
  deliveries: NotificationDelivery[]
  loading: boolean
  saving: boolean
  testingUuid: string | null
  error: string | null
}

export const useNotificationStore = defineStore('notification', {
  state: (): NotificationState => ({
    channels: [],
    deliveries: [],
    loading: false,
    saving: false,
    testingUuid: null,
    error: null,
  }),
  actions: {
    async loadNotifications(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        const [channelsResponse, deliveriesResponse] = await Promise.all([
          api.get<NotificationChannel[]>('/notifications/channels'),
          api.get<NotificationDelivery[]>('/notifications/deliveries'),
        ])
        this.channels = channelsResponse.data
        this.deliveries = deliveriesResponse.data
      } catch (error) {
        this.error = 'Notifications could not be loaded.'
      } finally {
        this.loading = false
      }
    },
    async createChannel(form: NotificationChannelForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.post<NotificationChannel>(
          '/notifications/channels',
          {
            name: form.name,
            driver: form.driver,
            enabled: form.enabled,
            config: this.configFromForm(form),
          },
        )
        this.channels = [...this.channels, response.data].sort((left, right) =>
          left.name.localeCompare(right.name),
        )
      } catch (error) {
        this.error = 'Notification channel could not be created.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async updateChannel(channelUuid: string, form: NotificationChannelForm): Promise<void> {
      this.saving = true
      this.error = null
      try {
        const response = await api.put<NotificationChannel>(
          `/notifications/channels/${channelUuid}`,
          {
            name: form.name,
            enabled: form.enabled,
            config: this.configFromForm(form),
          },
        )
        this.channels = this.channels
          .map((channel) => (channel.uuid === channelUuid ? response.data : channel))
          .sort((left, right) => left.name.localeCompare(right.name))
      } catch (error) {
        this.error = 'Notification channel could not be updated.'
        throw error
      } finally {
        this.saving = false
      }
    },
    async deleteChannel(channelUuid: string): Promise<void> {
      this.error = null
      try {
        await api.delete(`/notifications/channels/${channelUuid}`)
        this.channels = this.channels.filter((channel) => channel.uuid !== channelUuid)
      } catch (error) {
        this.error = 'Notification channel could not be deleted.'
        throw error
      }
    },
    async testChannel(channelUuid: string): Promise<void> {
      this.testingUuid = channelUuid
      this.error = null
      try {
        const response = await api.post<NotificationDelivery>(
          `/notifications/channels/${channelUuid}/test`,
          {},
        )
        this.deliveries = [response.data, ...this.deliveries]
      } catch (error) {
        this.error = 'Notification test could not be delivered.'
        throw error
      } finally {
        this.testingUuid = null
      }
    },
    configFromForm(form: NotificationChannelForm): Record<string, unknown> {
      if (form.driver === 'ntfy') {
        return {
          server_url: form.serverUrl,
          topic: form.topic,
          token: form.token || undefined,
        }
      }
      if (form.driver === 'webhook') {
        return {
          url: form.url,
          token: form.token || undefined,
        }
      }
      return { recipient: form.recipient }
    },
  },
})
