import { createRouter, createWebHistory } from 'vue-router';
import { useSessionStore } from '../stores/session';

const BACKEND_URL = 'http://127.0.0.1:8000';

const routes = [
  { path: '/', component: () => import('../views/HomeView.vue') },
  { path: '/login', component: () => import('../views/LoginView.vue') },
  { path: '/signup', component: () => import('../views/SignupView.vue') },
  { path: '/profile', component: () => import('../views/ProfileView.vue'), meta: { auth: true } },
  { path: '/onboarding', beforeEnter: () => { window.location.href = `${BACKEND_URL}/accounts/onboarding/`; } },
  { path: '/onboarding/gmail', beforeEnter: () => { window.location.href = `${BACKEND_URL}/accounts/onboarding/gmail/`; } },
  { path: '/onboarding/manual', beforeEnter: () => { window.location.href = `${BACKEND_URL}/accounts/onboarding/manual/`; } },
  { path: '/onboarding/complete', beforeEnter: () => { window.location.href = `${BACKEND_URL}/accounts/onboarding/complete/`; } },
  { path: '/subscriptions', component: () => import('../views/SubscriptionsView.vue'), meta: { auth: true } },
  { path: '/subscriptions/new', component: () => import('../views/AddSubscriptionView.vue'), meta: { auth: true } },
  { path: '/subscriptions/gmail', beforeEnter: () => { window.location.href = `${BACKEND_URL}/accounts/onboarding/gmail/`; } },
  { path: '/contents/search', component: () => import('../views/SearchView.vue') },
  { path: '/community', component: () => import('../views/CommunityView.vue') },
  { path: '/community/write', component: () => import('../views/CommunityWriteView.vue'), meta: { auth: true } },
  { path: '/community/:id', component: () => import('../views/CommunityDetailView.vue') },
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
