import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import HealthView from '../../views/HealthView.vue'
import HomeView from '../../views/HomeView.vue'
import { routesA } from './routes-a'
import { routesB } from './routes-b'

const sharedRoutes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/health', name: 'health', component: HealthView },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: [...sharedRoutes, ...routesA, ...routesB],
})
