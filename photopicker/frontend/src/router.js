import { createRouter, createWebHistory } from 'vue-router'
import ImportView from './views/ImportView.vue'
import PrescreenView from './views/PrescreenView.vue'
import PickView from './views/PickView.vue'
import PendingView from './views/PendingView.vue'
import ConfirmView from './views/ConfirmView.vue'
import FaceGroupsView from './views/FaceGroupsView.vue'

const routes = [
  { path: '/', redirect: '/import' },
  { path: '/import', component: ImportView },
  { path: '/prescreen', component: PrescreenView },
  { path: '/pick', component: PickView },
  { path: '/pending', component: PendingView },
  { path: '/face', component: FaceGroupsView },
  { path: '/confirm', component: ConfirmView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
