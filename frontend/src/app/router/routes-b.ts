import type { RouteRecordRaw } from 'vue-router'

export const routesB: RouteRecordRaw[] = [
  {
    path: '/b',
    name: 'member-b-dashboard',
    component: () => import('../../features/b/DashboardView.vue'),
  },
]
