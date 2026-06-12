import { createRouter, createWebHistory } from 'vue-router'
import ImportView from './views/ImportView.vue'
import PrescreenView from './views/PrescreenView.vue'
import PickView from './views/PickView.vue'
import ConfirmView from './views/ConfirmView.vue'

const routes = [
  { path: '/', redirect: '/import' },
  { path: '/import', component: ImportView },
  { path: '/prescreen', component: PrescreenView },
  { path: '/pick', component: PickView },
  { path: '/confirm', component: ConfirmView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
