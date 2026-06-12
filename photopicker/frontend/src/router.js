import { createRouter, createWebHistory } from 'vue-router'
import ImportView from './views/ImportView.vue'
import FilterView from './views/FilterView.vue'
import PickView from './views/PickView.vue'
import ExportView from './views/ExportView.vue'

const routes = [
  { path: '/', redirect: '/import' },
  { path: '/import', component: ImportView },
  { path: '/filter', component: FilterView },
  { path: '/pick', component: PickView },
  { path: '/export', component: ExportView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
