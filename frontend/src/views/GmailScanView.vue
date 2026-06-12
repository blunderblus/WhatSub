<script setup>
import { ref } from 'vue';
import { RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';

const emails = ref([]);
const loading = ref(false);
const error = ref('');
const saved = ref('');

async function scan() {
  loading.value = true;
  error.value = '';
  saved.value = '';
  try {
    const data = await apiRequest('/api/detector/gmail_detail/');
    if (data.error) throw new Error(data.error);
    emails.value = data.emails || [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function save(email) {
  const platform = guessPlatform(email.subject + ' ' + email.sender);
  await apiRequest('/api/accounts/onboarding/gmail/save/', {
    method: 'POST',
    body: {
      platform,
      plan_name: 'Gmail 감지',
      payment_amount: 0,
      billing_cycle: 'monthly',
    },
  });
  saved.value = `${platform} 항목을 저장했습니다. 금액과 갱신일은 내 구독에서 수정해 주세요.`;
}

function guessPlatform(text) {
  const lower = text.toLowerCase();
  const candidates = ['Netflix', 'Disney+', 'TVING', 'Wavve', 'Watcha', 'Coupang Play', 'Apple TV+', 'Amazon Prime Video', 'Spotify', 'OpenAI'];
  return candidates.find((name) => lower.includes(name.toLowerCase())) || '기타';
}
</script>

<template>
  <main class="panel">
    <div class="section-head">
      <div>
        <p class="eyebrow">Gmail scan</p>
        <h1>Gmail에서 구독 찾기</h1>
        <p class="muted">Google로 로그인한 계정의 최근 메일에서 구독 관련 메일을 찾아봅니다.</p>
      </div>
      <RouterLink class="button" to="/subscriptions/new">직접 추가</RouterLink>
    </div>

    <div class="actions">
      <button class="button primary" type="button" :disabled="loading" @click="scan">
        {{ loading ? '스캔 중' : '메일 스캔 시작' }}
      </button>
      <a class="button" href="/accounts/google/login/">Google 연결</a>
    </div>

    <p v-if="error" class="notice" style="margin-top: 18px">{{ error }}</p>
    <p v-if="saved" class="loader" style="margin-top: 18px">{{ saved }}</p>

    <div v-if="emails.length" class="email-list">
      <article v-for="email in emails" :key="`${email.subject}-${email.date}`" class="email-card">
        <div>
          <strong>{{ email.subject }}</strong>
          <span>{{ email.sender }} · {{ email.date }}</span>
        </div>
        <button class="button" type="button" @click="save(email)">구독으로 저장</button>
      </article>
    </div>
    <div v-else-if="!loading" class="empty" style="margin-top: 18px">스캔 결과가 여기에 표시됩니다.</div>
  </main>
</template>

<style scoped>
.email-list {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.email-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 13px;
  border: 1px solid #dce3e9;
  border-radius: 8px;
  background: #fff;
}

.email-card span {
  display: block;
  margin-top: 4px;
  color: #667586;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 620px) {
  .email-card {
    grid-template-columns: 1fr;
  }
}
</style>
