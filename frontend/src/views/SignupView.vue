<script setup>
import { onMounted, ref } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { backendRoutes, googleAuthUrl, redirectToBackend } from '../config/backend';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const route = useRoute();
const form = ref({ username: '', nickname: '', email: '', password1: '', password2: '' });
const error = ref('');
const googleHref = googleAuthUrl(undefined, 'signup');

onMounted(() => {
  if (route.query.error === 'no_account') {
    error.value = 'WhatSub에 가입된 Google 계정이 없습니다. Google로 가입하기를 진행해 주세요.';
  }
});

async function submit() {
  error.value = '';
  try {
    await session.signup(form.value);
    redirectToBackend(backendRoutes.onboarding);
  } catch (err) {
    error.value = Object.values(err.payload?.errors || {}).flat().join(' ') || err.message;
  }
}
</script>

<template>
  <main class="form-card auth-card">
    <p class="eyebrow">Create account</p>
    <h1>회원가입</h1>
    <p class="muted">구독 정보를 저장하고 결제 일정을 관리할 계정을 만듭니다.</p>
    <p v-if="error" class="notice">{{ error }}</p>

    <a class="button google full-width" :href="googleHref">
      <span class="google-mark" aria-hidden="true">G</span>
      Google로 가입하기
    </a>

    <div class="auth-divider" role="separator"><span>또는</span></div>

    <form @submit.prevent="submit">
      <div class="field"><label for="username">아이디</label><input id="username" v-model="form.username" required /></div>
      <div class="field"><label for="nickname">닉네임</label><input id="nickname" v-model="form.nickname" /></div>
      <div class="field"><label for="email">이메일</label><input id="email" v-model="form.email" type="email" /></div>
      <div class="form-row">
        <div class="field"><label for="password1">비밀번호</label><input id="password1" v-model="form.password1" type="password" required /></div>
        <div class="field"><label for="password2">비밀번호 확인</label><input id="password2" v-model="form.password2" type="password" required /></div>
      </div>
      <button class="button primary full-width" style="margin-top: 22px" type="submit">가입하고 시작하기</button>
    </form>
    <p class="muted">이미 계정이 있다면 <RouterLink to="/login">로그인</RouterLink>하세요.</p>
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
