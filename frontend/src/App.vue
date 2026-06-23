<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router';
import { useSessionStore } from './stores/session';
import WLogo from './components/WLogo.vue';

const session = useSessionStore();
const router = useRouter();

async function logout() {
  await session.logout();
  router.push('/');
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="WhatSub">
        <WLogo :size="36" />
        <span class="brand-text">WhatSub</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink to="/contents/movies">영화</RouterLink>
        <RouterLink to="/contents/shows">시리즈</RouterLink>
        <RouterLink to="/contents/search">작품 검색</RouterLink>
        <RouterLink to="/community">커뮤니티</RouterLink>
        <RouterLink v-if="session.isAuthenticated" to="/subscriptions">내 구독</RouterLink>
        <RouterLink v-if="session.isAuthenticated" class="profile-link" to="/profile" aria-label="내 프로필">
          <img v-if="session.user?.profile_image" :src="session.user.profile_image" alt="" />
          <span v-else class="nav-avatar" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" /></svg>
          </span>
          <span>{{ session.user?.nickname || session.user?.username }}</span>
        </RouterLink>
        <button v-if="session.isAuthenticated" class="nav-button" type="button" @click="logout">로그아웃</button>
        <RouterLink v-else to="/login">로그인</RouterLink>
        <RouterLink v-if="!session.isAuthenticated" class="accent-link" to="/signup">회원가입</RouterLink>
      </nav>
    </header>

    <RouterView />
  </div>
</template>

<style scoped>
.brand {
  gap: 10px;
}

.brand-text {
  font-family: Poppins, Pretendard, sans-serif;
  font-size: 22px;
  font-weight: 900;
  letter-spacing: -0.02em;
  color: var(--ws-text);
}

.profile-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.profile-link img,
.nav-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex: none;
}

.profile-link img {
  object-fit: cover;
}

.nav-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--ws-border);
  background: var(--ws-surface-2);
  color: var(--ws-muted);
}

.nav-avatar svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}
</style>
