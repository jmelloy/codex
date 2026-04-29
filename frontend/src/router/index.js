import { createRouter, createWebHistory } from 'vue-router'
import GalleryView from '../views/GalleryView.vue'
import DetailView from '../views/DetailView.vue'

const routes = [
  { path: '/', component: GalleryView },
  { path: '/image/:id', component: DetailView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
