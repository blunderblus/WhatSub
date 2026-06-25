<script setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter, RouterLink } from 'vue-router';
import { googleAuthUrl } from '../config/backend';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const router = useRouter();
const route = useRoute();
const username = ref('');
const password = ref('');
const error = ref('');
const googleHref = googleAuthUrl();

onMounted(() => {
  if (route.query.error === 'google') {
    error.value = 'Google 로그인에 실패했습니다. 다시 시도해 주세요.';
  }
});

async function submit() {
  error.value = '';
  try {
    await session.login({ username: username.value, password: password.value });
    router.push('/subscriptions');
  } catch (err) {
    error.value = err.message;
  }
}
</script>

<template>
  <main class="form-card auth-card">
    <p class="eyebrow">Welcome back</p>
    <h1>로그인</h1>
    <p class="muted">WhatSub 계정으로 내 구독 현황을 불러옵니다.</p>
    <p v-if="error" class="notice">{{ error }}</p>

    <a class="button google full-width" :href="googleHref">
      <span class="google-mark" aria-hidden="true">G</span>
      Google로 계속하기
    </a>

    <div class="auth-divider" role="separator"><span>또는</span></div>

    <form @submit.prevent="submit">
      <div class="field">
        <label for="username">아이디</label>
        <input id="username" v-model="username" autocomplete="username" required />
      </div>
      <div class="field">
        <label for="password">비밀번호</label>
        <input id="password" v-model="password" type="password" autocomplete="current-password" required />
      </div>
      <button class="button primary full-width" style="margin-top: 22px" type="submit">로그인</button>
    </form>
    <p class="muted">계정이 없다면 <RouterLink to="/signup">회원가입</RouterLink>으로 시작하세요.</p>
  </main>
</template>

<style scoped>
.auth-card {
  display: grid;
  gap: 0;
}

.auth-divider {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  margin: 18px 0;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 800;
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  height: 1px;
  background: var(--ws-border);
}

.button.google {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 4px;
  border-color: var(--ws-glass-border);
  background: rgba(255, 255, 255, 0.06);
  color: var(--ws-text);
  font-weight: 800;
  box-shadow: var(--ws-glass-highlight);
  backdrop-filter: blur(var(--ws-glass-blur));
}

.button.google:hover {
  border-color: rgba(var(--ws-primary-rgb), 0.45);
  background: rgba(255, 255, 255, 0.1);
}

.google-mark {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fff;
  color: #4285f4;
  font-size: 14px;
  font-weight: 900;
  line-height: 1;
}
</style>
