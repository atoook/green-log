import { createRouter, createWebHistory } from 'vue-router'
import PlantsPage from '../pages/PlantsPage.vue'
import PlantDetailPage from '../pages/PlantDetailPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/plants' },
    { path: '/plants', name: 'plants', component: PlantsPage },
    { path: '/plants/:plantId', name: 'plant-detail', component: PlantDetailPage },
  ],
})
