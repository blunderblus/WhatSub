<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const router = useRouter();
const form = ref({ username: '', nickname: '', email: '', password1: '', password2: '' });
const error = ref('');

async function submit() {
  error.value = '';
  try {
    await session.signup(form.value);
    router.push('/subscriptions/new');
  } catch (err) {
    error.value = Object.values(err.payload?.errors || {}).flat().join(' ') || err.message;
  }
}
</script>

<template>
  <main class="form-card">
    <p class="eyebrow">Create account</p>
    <h1>회원가입</h1>
    <p class="muted">구독 정보를 저장하고 결제 일정을 관리할 계정을 만듭니다.</p>
    <p v-if="error" class="notice">{{ error }}</p>
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
  </main>
</template>
