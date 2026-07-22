import { createRouter, createWebHistory } from 'vue-router'

import StorageView from '../views/StorageView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'storage',
      component: StorageView,
    },
  ],
})

export default router
