<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { apiRequest } from '../api/http';
import PageHeader from '../components/PageHeader.vue';

const router = useRouter();
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const questions = ref([]);
const genreOptions = ref([]);
const answers = ref({
  monthly_spend_cap: '',
  preferred_genre_ids: [],
  consumption_habits: {},
  platform_criteria: [],
  free_text: '',
});
const step = ref(0);

const habitQuestion = computed(() => questions.value.find((q) => q.id === 'consumption_habits'));
const criteriaQuestion = computed(() => questions.value.find((q) => q.id === 'platform_criteria'));
const visibleSteps = computed(() => [
  { key: 'budget', title: '예산' },
  { key: 'genres', title: '장르' },
  { key: 'habits', title: '습관' },
  { key: 'criteria', title: '기준' },
  { key: 'free', title: '자유 입력' },
]);

function toggleGenre(id) {
  const list = answers.value.preferred_genre_ids;
  const idx = list.indexOf(id);
  if (idx >= 0) list.splice(idx, 1);
  else list.push(id);
}

function toggleHabit(key) {
  answers.value.consumption_habits[key] = !answers.value.consumption_habits[key];
}

function toggleCriteria(key) {
  const list = answers.value.platform_criteria;
  const idx = list.indexOf(key);
  if (idx >= 0) list.splice(idx, 1);
  else list.push(key);
}

async function loadQuestions() {
  loading.value = true;
  try {
    const data = await apiRequest('/api/accounts/preferences/questions/');
    questions.value = data.questions || [];
    genreOptions.value = data.genre_options || [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function submit() {
  saving.value = true;
  error.value = '';
  try {
    const structured = {
      monthly_spend_cap: answers.value.monthly_spend_cap
        ? Number(answers.value.monthly_spend_cap)
        : null,
      preferred_genre_ids: answers.value.preferred_genre_ids,
      consumption_habits: answers.value.consumption_habits,
      platform_criteria: answers.value.platform_criteria,
    };
    const chat_messages = answers.value.free_text
      ? [{ role: 'user', content: answers.value.free_text }]
      : [];
    await apiRequest('/api/accounts/preferences/complete/', {
      method: 'POST',
      body: { structured_answers: structured, chat_messages },
    });
    router.push('/benchmark?tab=personal');
  } catch (err) {
    error.value = err.message;
  } finally {
    saving.value = false;
  }
}

function nextStep() {
  if (step.value < visibleSteps.value.length - 1) step.value += 1;
  else submit();
}

function prevStep() {
  if (step.value > 0) step.value -= 1;
}

onMounted(loadQuestions);
</script>

<template>
  <main class="pref-page">
    <PageHeader
      eyebrow="Onboarding"
      title="취향 설정 (선택)"
      description="AI가 예산·장르·습관을 바탕으로 Personal Score를 더 정확하게 계산합니다. 건너뛰어도 좋아요."
    />

    <p v-if="error" class="notice">{{ error }}</p>
    <div v-else-if="loading" class="loader">질문을 불러오는 중입니다.</div>

    <template v-else>
      <nav class="step-nav">
        <span
          v-for="(s, i) in visibleSteps"
          :key="s.key"
          class="step-dot"
          :class="{ active: i === step, done: i < step }"
        >{{ s.title }}</span>
      </nav>

      <section class="panel pref-panel">
        <template v-if="step === 0">
          <h2>월 OTT 예산 상한</h2>
          <p class="muted">스트리밍에 쓰고 싶은 월 최대 금액(원)을 입력해주세요.</p>
          <input
            v-model="answers.monthly_spend_cap"
            type="number"
            min="0"
            step="1000"
            placeholder="예: 30000"
            class="text-input"
          />
        </template>

        <template v-else-if="step === 1">
          <h2>선호 장르</h2>
          <p class="muted">자주 보는 장르를 골라주세요.</p>
          <div class="chip-grid">
            <button
              v-for="g in genreOptions"
              :key="g.id"
              type="button"
              class="chip"
              :class="{ active: answers.preferred_genre_ids.includes(g.id) }"
              @click="toggleGenre(g.id)"
            >{{ g.name }}</button>
          </div>
        </template>

        <template v-else-if="step === 2">
          <h2>구독 소비 습관</h2>
          <p class="muted">해당되는 항목을 선택해주세요.</p>
          <div class="chip-grid">
            <button
              v-for="opt in habitQuestion?.options || []"
              :key="opt.key"
              type="button"
              class="chip"
              :class="{ active: answers.consumption_habits[opt.key] }"
              @click="toggleHabit(opt.key)"
            >{{ opt.label }}</button>
          </div>
        </template>

        <template v-else-if="step === 3">
          <h2>플랫폼 선택 기준</h2>
          <p class="muted">구독할 때 중요하게 보는 기준을 골라주세요.</p>
          <div class="chip-grid">
            <button
              v-for="opt in criteriaQuestion?.options || []"
              :key="opt.key"
              type="button"
              class="chip"
              :class="{ active: answers.platform_criteria.includes(opt.key) }"
              @click="toggleCriteria(opt.key)"
            >{{ opt.label }}</button>
          </div>
        </template>

        <template v-else>
          <h2>추가 취향 (자유 입력)</h2>
          <p class="muted">최근 본 작품, 좋아하는 분위기, 피하고 싶은 장르 등을 적어주세요. AI가 파싱합니다.</p>
          <textarea
            v-model="answers.free_text"
            rows="5"
            class="text-input"
            placeholder="예: SF·스릴러 좋아하고 로맨스는 별로예요. 주말에 몰아보는 편이에요."
          ></textarea>
        </template>

        <div class="actions">
          <button v-if="step > 0" class="button" type="button" @click="prevStep">이전</button>
          <RouterLink class="button secondary" to="/benchmark">건너뛰기</RouterLink>
          <button class="button primary" type="button" :disabled="saving" @click="nextStep">
            {{ step < visibleSteps.length - 1 ? '다음' : (saving ? '저장 중...' : '완료') }}
          </button>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.pref-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 20px 48px;
}

.step-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.step-dot {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--ws-surface-2);
  border: 1px solid var(--ws-border);
  color: var(--ws-muted);
}

.step-dot.active {
  border-color: var(--ws-primary);
  color: var(--ws-primary);
  font-weight: 600;
}

.step-dot.done {
  background: var(--ws-surface);
}

.pref-panel {
  padding: 24px;
}

.pref-panel h2 {
  margin: 0 0 8px;
  font-size: 20px;
}

.text-input {
  width: 100%;
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
  color: inherit;
  font: inherit;
}

.chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.chip {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--ws-border);
  background: var(--ws-surface-2);
  cursor: pointer;
}

.chip.active {
  border-color: var(--ws-primary);
  background: var(--ws-primary);
  color: var(--ws-primary-fg);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 24px;
  justify-content: flex-end;
}
</style>
