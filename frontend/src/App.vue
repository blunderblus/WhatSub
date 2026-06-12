<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router';
import { useSessionStore } from './stores/session';

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
      <RouterLink class="brand" to="/" aria-label="WhatSub 홈">
        <img :src="'/img/whatsub-wordmark.png'" alt="WhatSub" />
      </RouterLink>
      <nav class="nav">
        <RouterLink to="/contents/movies">영화</RouterLink>
        <RouterLink to="/contents/shows">시리즈</RouterLink>
        <RouterLink to="/contents/search">작품 검색</RouterLink>
        <RouterLink v-if="session.isAuthenticated" to="/subscriptions">내 구독</RouterLink>
        <button v-if="session.isAuthenticated" class="nav-button" type="button" @click="logout">로그아웃</button>
        <RouterLink v-else to="/login">로그인</RouterLink>
        <RouterLink v-if="!session.isAuthenticated" class="accent-link" to="/signup">회원가입</RouterLink>
      </nav>
    </header>

    <RouterView />
  </div>
</template>
