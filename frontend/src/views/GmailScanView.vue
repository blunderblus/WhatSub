<script setup>
import { onMounted, ref } from 'vue';
import { useRouter, RouterLink } from 'vue-router';
import { apiRequest } from '../api/http';

const router = useRouter();
const subscriptions = ref([]);
const loading = ref(false);
const saving = ref(false);
const error = ref('');
const statusMessage = ref('');
const llmUsed = ref(false);
const emailCount = ref(0);

const cycleLabels = { monthly: '월간', annual: '연간', weekly: '주간' };

function money(value) {
  if (value === null || value === undefined || value === '') return '';
  return Number(value).toLocaleString('ko-KR');
}

async function scan() {
  loading.value = true;
  error.value = '';
  statusMessage.value = '받은편지함을 분석하는 중입니다…';
  try {
    const data = await apiRequest('/api/detector/gmail_detail/');
    if (data.error) throw new Error(data.error);

    emailCount.value = data.email_count || 0;
    llmUsed.value = Boolean(data.llm_used);
    subscriptions.value = (data.subscriptions || []).map((sub) => ({
      ...sub,
      selected: true,
      payment_amount: sub.payment_amount ?? '',
      plan_name: sub.plan_name || '',
      billing_cycle: sub.billing_cycle || 'monthly',
      renewal_date: sub.renewal_date || '',
    }));
    statusMessage.value = data.message || '';
  } catch (err) {
    error.value = err.message === 'social token not found'
      ? 'Gmail에 연결되어 있지 않습니다. Google 계정을 연결해 주세요.'
      : err.message;
    statusMessage.value = '';
  } finally {
    loading.value = false;
  }
}

async function saveSelected() {
  const selected = subscriptions.value.filter((sub) => sub.selected && sub.platform);
  if (!selected.length) {
    error.value = '저장할 구독을 하나 이상 선택해 주세요.';
    return;
  }

  saving.value = true;
  error.value = '';
  try {
    await apiRequest('/api/accounts/onboarding/gmail/save-bulk/', {
      method: 'POST',
      body: { subscriptions: selected },
    });
    router.push('/onboarding/complete');
  } catch (err) {
    error.value = err.message;
  } finally {
    saving.value = false;
  }
}

function skipToComplete() {
  router.push('/onboarding/complete');
}

onMounted(scan);
</script>

<template>
  <main class="panel">
    <div class="section-head">
      <div>
        <p class="eyebrow">Gmail Detection</p>
        <h1>받은편지함에서 구독 찾기</h1>
        <p class="muted">최근 3개월 내 결제·구독 관련 메일을 분석합니다.</p>
      </div>
      <RouterLink class="button" to="/onboarding">← 뒤로</RouterLink>
    </div>

    <div class="actions">
      <button class="button primary" type="button" :disabled="loading" @click="scan">
        {{ loading ? '스캔 중…' : '다시 스캔' }}
      </button>
      <a class="button" href="/accounts/google/login/?process=connect">Google 연결</a>
    </div>

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <p v-if="emailCount && subscriptions.length" class="meta">
      {{ emailCount }}건의 관련 메일 분석
      <span v-if="llmUsed"> · AI 추출 적용</span>
      <span v-else> · 규칙 기반 추출</span>
    </p>
    <p v-if="error" class="notice" style="margin-top: 12px">{{ error }}</p>

    <div v-if="subscriptions.length" class="sub-list">
      <article v-for="(sub, idx) in subscriptions" :key="idx" class="sub-card">
        <label class="check">
          <input v-model="sub.selected" type="checkbox" />
        </label>
        <div class="fields">
          <div class="field">
            <label>플랫폼</label>
            <input v-model="sub.platform" type="text" />
          </div>
          <div class="field">
            <label>요금제</label>
            <input v-model="sub.plan_name" type="text" placeholder="미정" />
          </div>
          <div class="field">
            <label>금액 (원)</label>
            <input v-model="sub.payment_amount" type="number" min="0" placeholder="0" />
          </div>
          <div class="field">
            <label>결제 주기</label>
            <select v-model="sub.billing_cycle">
              <option value="weekly">주간</option>
              <option value="monthly">월간</option>
              <option value="annual">연간</option>
            </select>
          </div>
          <div class="field wide">
            <label>갱신일</label>
            <input v-model="sub.renewal_date" type="date" />
          </div>
          <p v-if="sub.source_subject" class="source">{{ sub.source_subject }}</p>
        </div>
        <div class="badge">{{ cycleLabels[sub.billing_cycle] || sub.billing_cycle }}</div>
      </article>
    </div>

    <div v-else-if="!loading && !error" class="empty" style="margin-top: 18px">
      구독을 찾지 못했습니다. Google 계정 연결 후 다시 시도하거나 직접 추가해 보세요.
    </div>

    <div v-if="subscriptions.length" class="footer-actions">
      <button class="button primary" type="button" :disabled="saving" @click="saveSelected">
        {{ saving ? '저장 중…' : '선택 항목 저장하고 완료' }}
      </button>
      <button class="button" type="button" @click="skipToComplete">건너뛰기</button>
    </div>
  </main>
</template>

<style scoped>
.status {
  margin-top: 18px;
  padding: 16px;
  border: 1px solid #dce3e9;
  border-radius: 10px;
  background: #fff;
  color: #45525e;
}

.meta {
  margin-top: 8px;
  color: #8a97a2;
  font-size: 13px;
  font-weight: 700;
}

.sub-list {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.sub-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 14px;
  align-items: start;
  padding: 16px;
  border: 1px solid #dce3e9;
  border-radius: 12px;
  background: #fff;
}

.check {
  padding-top: 28px;
}

.fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.field {
  display: grid;
  gap: 4px;
}

.field.wide {
  grid-column: 1 / -1;
}

.field label {
  font-size: 12px;
  font-weight: 800;
  color: #687785;
}

.field input,
.field select {
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid #c8d1da;
  border-radius: 7px;
  font: inherit;
}

.source {
  grid-column: 1 / -1;
  margin: 0;
  color: #93a0ab;
  font-size: 12px;
}

.badge {
  padding: 6px 10px;
  border-radius: 999px;
  background: #eef6f6;
  color: #2f6f73;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.footer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}

@media (max-width: 720px) {
  .sub-card {
    grid-template-columns: 1fr;
  }

  .check {
    padding-top: 0;
  }

  .fields {
    grid-template-columns: 1fr;
  }
}
</style>
