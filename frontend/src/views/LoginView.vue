<script setup>
import { ref } from 'vue';
import { useRouter, RouterLink } from 'vue-router';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const router = useRouter();
const username = ref('');
const password = ref('');
const error = ref('');

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
  <main class="form-card">
    <p class="eyebrow">Welcome back</p>
    <h1>로그인</h1>
    <p class="muted">WhatSub 계정으로 내 구독 현황을 불러옵니다.</p>
    <p v-if="error" class="notice">{{ error }}</p>
    <form @submit.prevent="submit">
      <div class="field">
        <label for="username">아이디</label>
        <input id="username" v-model="username" autocomplete="username" required />
      </div>
      <div class="field">
        <label for="password">비밀번호</label>
        <input id="password" v-model="password" type="password" autocomplete="current-password" required />
      </div>
      <div class="actions" style="margin-top: 22px">
        <button class="button primary full-width" type="submit">로그인</button>
        <a class="button full-width" href="/accounts/google/login/">Google로 로그인</a>
      </div>
    </form>
    <p class="muted">계정이 없다면 <RouterLink to="/signup">회원가입</RouterLink>으로 시작하세요.</p>
  </main>
</template>
