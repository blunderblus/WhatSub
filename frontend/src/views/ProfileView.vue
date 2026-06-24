<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { apiRequest } from '../api/http';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const session = useSessionStore();
const form = ref({ nickname: '', profile_image: '' });
const message = ref('');
const error = ref('');
const saving = ref(false);

onMounted(() => {
  form.value.nickname = session.user?.nickname || session.user?.username || '';
  form.value.profile_image = session.user?.profile_image || '';
});

async function submit() {
  message.value = '';
  error.value = '';
  saving.value = true;
  try {
    const data = await apiRequest('/api/accounts/profile/', {
      method: 'PATCH',
      body: form.value,
    });
    session.user = data.user;
    message.value = '저장되었습니다.';
    setTimeout(() => router.push('/community'), 500);
  } catch (err) {
    error.value = Object.values(err.payload || {}).flat().join(' ') || err.message;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <main class="form-card profile-card">
    <p class="eyebrow">Profile</p>
    <h1>내 프로필</h1>
    <p class="muted">커뮤니티에서 보여줄 닉네임을 설정합니다.</p>

    <div class="profile-preview">
      <img v-if="form.profile_image" :src="form.profile_image" alt="" />
      <span v-else class="default-avatar" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" /></svg>
      </span>
      <strong>{{ form.nickname || session.user?.username }}</strong>
    </div>

    <p v-if="message" class="notice success">{{ message }}</p>
    <p v-if="error" class="notice">{{ error }}</p>

    <form @submit.prevent="submit">
      <div class="field">
        <label for="nickname">닉네임</label>
        <input id="nickname" v-model.trim="form.nickname" maxlength="30" required />
      </div>
      <div class="field">
        <label for="profile_image">프로필 이미지 URL</label>
        <input id="profile_image" v-model.trim="form.profile_image" type="url" placeholder="https://..." />
      </div>
      <button class="button primary full-width" style="margin-top: 22px" type="submit" :disabled="saving">
        {{ saving ? '저장 중' : '저장하기' }}
      </button>
    </form>
  </main>
</template>

<style scoped>
.profile-card {
  max-width: 560px;
}

.profile-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 0;
  padding: 14px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
}

.profile-preview img,
.default-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  flex: none;
}

.profile-preview img {
  object-fit: cover;
}

.default-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--ws-border);
  background: var(--ws-surface);
  color: var(--ws-muted);
}

.default-avatar svg {
  width: 24px;
  height: 24px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.success {
  border-color: rgba(217, 221, 146, 0.35);
  background: rgba(217, 221, 146, 0.08);
  color: var(--ws-primary);
}
</style>
