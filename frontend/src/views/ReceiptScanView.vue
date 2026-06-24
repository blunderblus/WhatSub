<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import PageHeader from '../components/PageHeader.vue';
import { extractReceiptImages, saveDetectedSubscriptions } from '../api/receipt';
import { apiRequest } from '../api/http';
import { backendRoutes, redirectToBackend, backendUrl } from '../config/backend';
import { navigateWithOnboardingNav } from '../utils/onboardingNav';

const SUBSCRIBE_RETURN = `${backendRoutes.onboarding}?phase=subscribe`;

const route = useRoute();
const router = useRouter();

const isOnboarding = computed(() => route.query.onboarding === '1');
const platforms = ref([]);
const plans = ref([]);
const previews = ref([]);
const subscriptions = ref([]);
const analyzing = ref(false);
const saving = ref(false);
const error = ref('');
const success = ref('');
const isDragging = ref(false);
const fileInputRef = ref(null);

function plansForPlatform(platformId) {
  if (!platformId) return [];
  return plans.value.filter((plan) => String(plan.platform) === String(platformId));
}

function platformNameById(platformId) {
  return platforms.value.find((item) => String(item.id) === String(platformId))?.name || '';
}

function guessPlanId(platformId, planName) {
  if (!platformId || !planName) return null;
  const normalized = planName.trim().toLowerCase();
  const candidates = plansForPlatform(platformId);
  const exact = candidates.find((plan) => plan.plan_name.toLowerCase() === normalized);
  if (exact) return exact.id;
  const partial = candidates.find(
    (plan) => normalized.includes(plan.plan_name.toLowerCase())
      || plan.plan_name.toLowerCase().includes(normalized),
  );
  return partial?.id || null;
}

function applyPlanToItem(item) {
  if (!item.plan_id) return;
  const plan = plans.value.find((entry) => String(entry.id) === String(item.plan_id));
  if (!plan) return;
  if (!item.plan_name) item.plan_name = plan.plan_name;
  if (item.payment_amount === '' || item.payment_amount == null) item.payment_amount = plan.price;
  if (!item.billing_cycle) item.billing_cycle = plan.billing_period;
}

function normalizeDetectedItem(item, index) {
  const platformId = item.platform_id || null;
  const planId = item.plan_id || guessPlanId(platformId, item.plan_name);
  const matched = Boolean(item.platform_matched && platformId);
  const normalized = {
    ...item,
    id: item.id || `receipt-${index}-${Date.now()}`,
    selected: item.selected !== false,
    platform_id: platformId,
    platform_matched: matched,
    platform: matched ? (item.catalog_platform_name || platformNameById(platformId) || item.platform || '') : (item.platform || ''),
    plan_id: planId || '',
    custom: !matched,
  };
  applyPlanToItem(normalized);
  return normalized;
}

function onPlatformChange(item) {
  if (!item.platform_id) {
    item.platform_matched = false;
    item.custom = true;
    item.plan_id = null;
    return;
  }
  item.platform_matched = true;
  item.custom = false;
  item.platform = platformNameById(item.platform_id);
  item.plan_id = null;
  item.plan_name = '';
}

function onPlanChange(item) {
  if (!item.plan_id) return;
  const plan = plans.value.find((entry) => String(entry.id) === String(item.plan_id));
  if (!plan) return;
  item.plan_name = plan.plan_name;
  item.payment_amount = plan.price;
  item.billing_cycle = plan.billing_period;
}

function payloadForSave(item) {
  const platformName = item.platform_matched && item.platform_id
    ? platformNameById(item.platform_id)
    : (item.platform || '').trim();
  return {
    platform: platformName,
    platform_id: item.platform_matched && item.platform_id ? item.platform_id : null,
    plan_id: item.plan_id || null,
    plan_name: item.plan_name,
    payment_amount: item.payment_amount,
    billing_cycle: item.billing_cycle,
    renewal_date: item.renewal_date,
    payment_method: item.payment_method,
    selected: item.selected,
  };
}

function readFiles(fileList) {
  error.value = '';
  success.value = '';
  const files = Array.from(fileList || []).filter((file) => file.type.startsWith('image/') || /\.(png|jpe?g|webp)$/i.test(file.name));
  if (!files.length) {
    error.value = '이미지 파일을 선택해 주세요.';
    return;
  }
  previews.value.forEach((item) => URL.revokeObjectURL(item.url));
  const merged = [...previews.value.map((item) => item.file), ...files].slice(0, 5);
  previews.value = merged.map((file) => ({
    file,
    name: file.name,
    url: URL.createObjectURL(file),
  }));
  subscriptions.value = [];
}

function onDragOver() {
  isDragging.value = true;
}

function onDragLeave() {
  isDragging.value = false;
}

function onDrop(event) {
  isDragging.value = false;
  readFiles(event.dataTransfer?.files);
}

function openFilePicker() {
  fileInputRef.value?.click();
}

async function analyze() {
  if (!previews.value.length) {
    error.value = '먼저 결제내역 또는 구독 화면 이미지를 업로드해 주세요.';
    return;
  }
  analyzing.value = true;
  error.value = '';
  success.value = '';
  try {
    const data = await extractReceiptImages(previews.value.map((item) => item.file));
    subscriptions.value = (data.subscriptions || []).map((item, index) => normalizeDetectedItem(item, index));
    if (!subscriptions.value.length) {
      error.value = '구독 정보를 찾지 못했습니다. 다른 각도의 스크린샷을 시도해 보세요.';
    }
  } catch (err) {
    subscriptions.value = [];
    error.value = err.payload?.detail || err.message;
  } finally {
    analyzing.value = false;
  }
}

function addManualRow() {
  subscriptions.value.push({
    id: `manual-${Date.now()}`,
    platform: '',
    platform_id: null,
    plan_id: null,
    plan_name: '',
    payment_amount: '',
    billing_cycle: 'monthly',
    renewal_date: '',
    payment_method: '',
    selected: true,
    platform_matched: false,
    custom: true,
  });
}

function removeRow(id) {
  subscriptions.value = subscriptions.value.filter((item) => item.id !== id);
}

async function saveSelected() {
  const selected = subscriptions.value.filter((item) => item.selected);
  if (!selected.length) {
    error.value = '저장할 구독을 하나 이상 선택해 주세요.';
    return;
  }
  saving.value = true;
  error.value = '';
  try {
    const data = await saveDetectedSubscriptions(
      selected.map((item) => payloadForSave(item)),
      'receipt',
    );
    success.value = `${data.saved_count}개 구독을 저장했습니다.`;
    if (isOnboarding.value) {
      navigateWithOnboardingNav(
        backendUrl(`${backendRoutes.onboarding}?phase=subscribe_continue&saved=receipt`),
        '온보딩으로 돌아오는 중…',
      );
      return;
    }
    router.push('/subscriptions');
  } catch (err) {
    error.value = err.payload?.detail || err.message;
  } finally {
    saving.value = false;
  }
}

function goBack() {
  if (isOnboarding.value) {
    navigateWithOnboardingNav(backendUrl(SUBSCRIBE_RETURN), '온보딩으로 돌아가는 중…');
    return;
  }
  router.push('/subscriptions/new');
}

onMounted(async () => {
  if (isOnboarding.value) {
    const methodIndex = route.query.method_index ?? '1';
    apiRequest('/api/accounts/onboarding/resume/', {
      method: 'POST',
      body: { step: 'method_pick', method_key: 'receipt', method_index: Number(methodIndex) || 1 },
    }).catch(() => {});
  }
  const [platformData, planData] = await Promise.all([
    apiRequest('/api/subscriptions/platforms/'),
    apiRequest('/api/subscriptions/plans/'),
  ]);
  platforms.value = platformData;
  plans.value = planData;
});
</script>

<template>
  <main class="receipt-page">
    <PageHeader
      eyebrow="Payment Scan"
      :title="isOnboarding ? '결제내역·이미지로 구독 찾기' : '결제내역·이미지로 구독 추가'"
    />

    <section class="panel intro">
      <p class="muted">
        결제 내역, 앱스토어 구독 화면, 카드 결제 알림 캡처 등을 업로드하면
        AI가 플랫폼·요금·결제 주기·다음 결제일을 추출합니다.
      </p>
      <ul class="tips muted small">
        <li>PNG, JPG, WEBP · 파일당 5MB 이하 · 최대 5장</li>
        <li>PC에서는 이미지를 드래그 앤 드롭하거나 클릭해 첨부할 수 있습니다</li>
        <li>업로드된 이미지는 분석 후 서버에 저장하지 않습니다</li>
      </ul>
    </section>

    <section class="panel upload-panel">
      <div
        class="upload-zone"
        :class="{ dragging: isDragging }"
        @dragover.prevent="onDragOver"
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInputRef"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          multiple
          capture="environment"
          @change="readFiles($event.target.files); $event.target.value = ''"
        />
        <button class="upload-trigger" type="button" @click="openFilePicker">
          <strong>📷 이미지 선택 · 드래그 앤 드롭</strong>
          <span class="muted small">클릭하거나 파일을 여기에 놓으세요 (모바일: 촬영 가능)</span>
        </button>
      </div>

      <div v-if="previews.length" class="preview-grid">
        <figure v-for="item in previews" :key="item.url">
          <img :src="item.url" :alt="item.name" />
          <figcaption>{{ item.name }}</figcaption>
        </figure>
      </div>

      <div class="actions">
        <button class="button" type="button" @click="goBack">← 뒤로</button>
        <button
          class="button primary"
          type="button"
          :disabled="!previews.length || analyzing"
          @click="analyze"
        >
          {{ analyzing ? 'AI 분석 중…' : 'AI로 구독 정보 추출' }}
        </button>
      </div>
    </section>

    <p v-if="error" class="notice">{{ error }}</p>
    <p v-if="success" class="notice success">{{ success }}</p>

    <section v-if="subscriptions.length" class="results panel">
      <div class="results-head">
        <div>
          <h2>추출 결과</h2>
          <p class="results-sub muted">AI가 찾은 구독 정보를 확인하고 수정한 뒤 저장하세요.</p>
        </div>
        <button class="button" type="button" @click="addManualRow">+ 직접 추가</button>
      </div>

      <article v-for="item in subscriptions" :key="item.id" class="sub-card">
        <header class="sub-card-head">
          <label class="select-row">
            <input v-model="item.selected" type="checkbox" class="select-check" />
            <span class="match-badge" :class="{ matched: item.platform_matched }">
              {{ item.platform_matched ? '공식 플랫폼 매칭됨' : '수동 확인 필요' }}
            </span>
          </label>
          <button type="button" class="remove-btn" aria-label="삭제" @click="removeRow(item.id)">삭제</button>
        </header>

        <div class="fields">
          <label v-if="item.platform_matched && item.platform_id" class="field field-full">
            <span class="field-label">플랫폼</span>
            <select v-model="item.platform_id" @change="onPlatformChange(item)">
              <option v-for="platform in platforms" :key="platform.id" :value="platform.id">
                {{ platform.name }}
              </option>
            </select>
          </label>
          <label v-else class="field field-full">
            <span class="field-label">플랫폼</span>
            <input v-model="item.platform" type="text" required placeholder="Netflix, TVING 등" />
          </label>

          <div class="form-row">
            <label v-if="item.platform_matched && item.platform_id" class="field">
              <span class="field-label">요금제</span>
              <select v-model="item.plan_id" @change="onPlanChange(item)">
                <option value="">직접 입력</option>
                <option
                  v-for="plan in plansForPlatform(item.platform_id)"
                  :key="plan.id"
                  :value="plan.id"
                >
                  {{ plan.plan_name }} · {{ Number(plan.price).toLocaleString('ko-KR') }}원
                </option>
              </select>
            </label>
            <label class="field" :class="{ 'field-full': !(item.platform_matched && item.platform_id) }">
              <span class="field-label">{{ item.platform_matched && item.platform_id ? '요금제 이름' : '요금제' }}</span>
              <input v-model="item.plan_name" type="text" placeholder="프리미엄, 베이직 등" />
            </label>
            <label class="field">
              <span class="field-label">금액 (원)</span>
              <input v-model="item.payment_amount" type="number" min="0" inputmode="numeric" placeholder="17000" />
            </label>
          </div>

          <div class="form-row">
            <label class="field">
              <span class="field-label">결제 주기</span>
              <select v-model="item.billing_cycle">
                <option value="monthly">월간</option>
                <option value="annual">연간</option>
                <option value="weekly">주간</option>
              </select>
            </label>
            <label class="field">
              <span class="field-label">다음 결제일</span>
              <input v-model="item.renewal_date" type="date" />
            </label>
          </div>

          <label class="field field-full">
            <span class="field-label">결제 수단</span>
            <input v-model="item.payment_method" type="text" placeholder="신한카드, Apple Pay 등" />
          </label>
        </div>
      </article>

      <div class="actions results-actions">
        <button class="button primary full-width" type="button" :disabled="saving" @click="saveSelected">
          {{ saving ? '저장 중…' : '선택 항목 저장' }}
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.receipt-page {
  display: grid;
  gap: 20px;
  max-width: 920px;
  margin: 0 auto;
}

.intro ul {
  margin: 10px 0 0;
  padding-left: 18px;
}

.upload-zone {
  display: grid;
  place-items: center;
  padding: 8px;
  border: 2px dashed var(--ws-border);
  border-radius: 12px;
  transition: border-color 160ms, background 160ms;
}

.upload-zone.dragging {
  border-color: var(--ws-primary);
  background: rgba(var(--ws-primary-rgb), 0.08);
}

.upload-zone input {
  display: none;
}

.upload-trigger {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 28px 20px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: center;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.preview-grid figure {
  margin: 0;
}

.preview-grid img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--ws-border);
}

.preview-grid figcaption {
  margin-top: 4px;
  font-size: 11px;
  color: var(--ws-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.results-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.results-head h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 900;
  letter-spacing: -0.02em;
}

.results-sub {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.5;
}

.sub-card {
  display: grid;
  gap: 18px;
  padding: 22px 24px;
  margin-bottom: 16px;
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.28);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(var(--ws-secondary-rgb), 0.08), var(--ws-surface-2));
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
}

.sub-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(var(--ws-secondary-rgb), 0.18);
}

.select-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  cursor: pointer;
}

.select-check {
  width: 22px;
  height: 22px;
  accent-color: var(--ws-primary);
  cursor: pointer;
}

.match-badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 180, 180, 0.12);
  color: #ffb4b4;
  font-size: 13px;
  font-weight: 800;
}

.match-badge.matched {
  background: rgba(var(--ws-primary-rgb), 0.14);
  color: var(--ws-primary);
}

.fields {
  display: grid;
  gap: 16px;
}

.field {
  display: grid;
  gap: 8px;
  margin: 0;
}

.field-full {
  grid-column: 1 / -1;
}

.field-label {
  color: var(--ws-muted);
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.field input,
.field select {
  width: 100%;
  min-height: 54px;
  padding: 12px 16px;
  border: 1px solid rgba(var(--ws-secondary-rgb), 0.28);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.18);
  color: var(--ws-text);
  font-size: 16px;
  font-weight: 700;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.field input::placeholder {
  color: var(--ws-muted);
  opacity: 0.75;
  font-weight: 600;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: var(--ws-primary);
  box-shadow: 0 0 0 3px rgba(var(--ws-primary-rgb), 0.16);
}

.field select {
  cursor: pointer;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.remove-btn {
  flex: none;
  min-height: 44px;
  padding: 0 16px;
  border: 1px solid rgba(255, 77, 77, 0.28);
  border-radius: 12px;
  background: rgba(255, 77, 77, 0.1);
  color: #ffb4b4;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.remove-btn:hover {
  border-color: rgba(255, 120, 120, 0.5);
  background: rgba(255, 77, 77, 0.16);
}

.results-actions {
  margin-top: 8px;
}

.results-actions .button.primary {
  min-height: 54px;
  font-size: 16px;
  font-weight: 900;
}

.notice.success {
  border-color: rgba(217, 221, 146, 0.35);
  background: rgba(217, 221, 146, 0.08);
  color: var(--ws-primary);
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .sub-card {
    padding: 18px 16px;
  }

  .sub-card-head {
    flex-direction: column;
    align-items: stretch;
  }

  .remove-btn {
    width: 100%;
  }
}
</style>
