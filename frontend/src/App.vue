<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router';
import { useSessionStore } from './stores/session';
import { profileInitial } from './utils/formatters';
import WLogo from './components/WLogo.vue';
import NotificationBell from './components/NotificationBell.vue';
import UrgentNotificationToast from './components/UrgentNotificationToast.vue';

const session = useSessionStore();
const router = useRouter();

async function logout() {
  await session.logout();
  router.push('/');
}
</script>

<template>
  <div class="app-shell app-glass">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="WhatSub">
        <WLogo :size="36" />
        <span class="brand-text">WhatSub</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink to="/contents/movies">영화</RouterLink>
        <RouterLink to="/contents/shows">시리즈</RouterLink>
        <RouterLink to="/contents/search">작품 검색</RouterLink>
        <RouterLink to="/benchmark">OTT순위</RouterLink>
        <RouterLink to="/community">커뮤니티</RouterLink>
        <NotificationBell v-if="session.isAuthenticated" />
        <RouterLink v-if="session.isAuthenticated" class="profile-link" to="/profile" aria-label="내 프로필">
          <img v-if="session.user?.profile_image" :src="session.user.profile_image" alt="" />
          <span v-else class="nav-avatar avatar-initial-letter" aria-hidden="true">
            {{ profileInitial(session.user?.nickname || session.user?.username) }}
          </span>
          <span>{{ session.user?.nickname || session.user?.username }}</span>
        </RouterLink>
        <button v-if="session.isAuthenticated" class="nav-button" type="button" @click="logout">로그아웃</button>
        <RouterLink v-else to="/login">로그인</RouterLink>
        <RouterLink v-if="!session.isAuthenticated" class="accent-link" to="/signup">회원가입</RouterLink>
      </nav>
    </header>

    <RouterView />
    <UrgentNotificationToast v-if="session.isAuthenticated" />
  </div>
</template>

<style scoped>
.brand {
  gap: 10px;
}

.brand-text {
  font-family: Comfortaa, "Asta Sans", sans-serif;
  font-size: 22px;
  font-weight: 900;
  letter-spacing: -0.02em;
  color: var(--ws-text);
  text-shadow: 0 0 28px rgba(var(--ws-primary-rgb), 0.25);
}

.profile-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  line-height: 1;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--ws-radius-pill);
  padding: 4px 10px 4px 4px !important;
  background: rgba(255, 255, 255, 0.05);
  box-shadow: var(--ws-glass-highlight);
}

.profile-link:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(var(--ws-primary-rgb), 0.3);
}

.profile-link img,
.nav-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex: none;
  border: none;
  box-shadow: none;
}

.profile-link img {
  display: block;
  object-fit: cover;
}

.nav-avatar {
  font-size: 12px;
}
</style>
