import { createRouter, createWebHistory } from 'vue-router'

import BackupsView from '../views/BackupsView.vue'
import DashboardView from '../views/DashboardView.vue'
import RestoreView from '../views/RestoreView.vue'
import SchedulerView from '../views/SchedulerView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { title: 'Dashboard' },
    },
    {
      path: '/backups',
      name: 'backups',
      component: BackupsView,
      meta: { title: 'Backups' },
    },
    {
      path: '/restore',
      name: 'restore',
      component: RestoreView,
      meta: { title: 'Restore' },
    },
    {
      path: '/scheduler',
      name: 'scheduler',
      component: SchedulerView,
      meta: { title: 'Scheduler' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { title: 'Settings' },
    },
  ],
})

export default router
