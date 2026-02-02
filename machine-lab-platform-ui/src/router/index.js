import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '../pages/LoginPage.vue';
import Dashboard from '../pages/DashboardPage.vue';
import HostManagement from '../pages/HostManagement.vue';
import SettingsPage from '../pages/AuthenticationPage.vue';
import { isAuthenticated } from '../utils/auth';

const routes = [
  { path: '/', component: LoginPage },
  { path: '/dashboard', component: Dashboard, meta: { requiresAuth: true } },
  { path: '/hosts', component: HostManagement, meta: { requiresAuth: true } },
  { path: '/settings', component: SettingsPage, meta: { requiresAuth: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    next('/');
  } else {
    next();
  }
});

export default router;