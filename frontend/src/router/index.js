import { createRouter, createWebHistory } from 'vue-router';
import { useSessionStore } from '../stores/session';

const routes = [
  { path: '/', component: () => import('../views/HomeView.vue') },
  { path: '/login', component: () => import('../views/LoginView.vue') },
  { path: '/signup', component: () => import('../views/SignupView.vue') },
  { path: '/subscriptions', component: () => import('../views/SubscriptionsView.vue'), meta: { auth: true } },
  { path: '/subscriptions/new', component: () => import('../views/AddSubscriptionView.vue'), meta: { auth: true } },
  { path: '/subscriptions/gmail', component: () => import('../views/GmailScanView.vue'), meta: { auth: true } },
  { path: '/contents/search', component: () => import('../views/SearchView.vue') },
  { path: '/contents/:type(movies|shows)', component: () => import('../views/ContentListView.vue') },
  { path: '/contents/:type(movies|shows)/:id', component: () => import('../views/ContentDetailView.vue') },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach(async (to) => {
  const session = useSessionStore();

  if (session.loading) {
    await session.refresh();
  }

  if (to.meta.auth && !session.isAuthenticated) {
    return '/login';
  }

  if ((to.path === '/login' || to.path === '/signup') && session.isAuthenticated) {
    return '/subscriptions';
  }

  return true;
});

export default router;
