import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import App from './App.vue'
import EnvironmentView from './views/EnvironmentView.vue'
import { equipmentPreset } from './theme'
import 'primeicons/primeicons.css'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/environment' },
    { path: '/environment', component: EnvironmentView },
    { path: '/:pathMatch(.*)*', redirect: '/environment' },
  ],
})

createApp(App)
  .use(router)
  .use(PrimeVue, {
    theme: { preset: equipmentPreset, options: { darkModeSelector: false } },
  })
  .mount('#app')
