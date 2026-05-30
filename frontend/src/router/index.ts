import { createRouter, createWebHistory } from 'vue-router'
import PlantsPage from '../pages/PlantsPage.vue'
import PlantDetailPage from '../pages/PlantDetailPage.vue'
import TodayCarePage from '../pages/TodayCarePage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/plants' },
    {
      path: '/care/today',
      name: 'today-care',
      component: TodayCarePage,
      meta: { requiresAuth: true },
    },
    { path: '/plants', name: 'plants', component: PlantsPage, meta: { requiresAuth: true } },
    {
      path: '/plants/:plantId',
      name: 'plant-detail',
      component: PlantDetailPage,
      meta: { requiresAuth: true },
    },
  ],
})
