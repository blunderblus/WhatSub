<script setup>
import { computed, onMounted, ref } from 'vue';
import { useSubscriptionPlanPicker } from '../composables/useSubscriptionPlanPicker';
import { useSubscriptionSaver } from '../composables/useSubscriptionSaver';
import {
  billingLabel,
  buildCalcItemFromPlan,
  formatWon,
  itemTypeLabel,
  planMonthlyPrice,
} from '../utils/billing';

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  existingMonthly: {
    type: Number,
    default: 0,
  },
  monthlyBudget: {
    type: Number,
    default: null,
  },
});

const emit = defineEmits(['update:modelValue', 'drop-plan', 'add-plan']);

const {
  platforms,
  filteredPlans,
  selectedPlatformId,
  selectedPlanId,
  selectedPlan,
  loading: plansLoading,
  error: plansError,
  load: loadPlans,
} = useSubscriptionPlanPicker();

const subscriptionSaver = useSubscriptionSaver();
const checkedItemIds = ref(new Set());

const calcTotal = computed(() =>
  props.modelValue.reduce((sum, item) => sum + Number(item.monthly_price || 0), 0),
);

const platformWebsiteById = computed(() =>
  new Map(platforms.value.map((platform) => [String(platform.id), platform.website_url])),
);

const projectedTotal = computed(() => props.existingMonthly + calcTotal.value);

const budgetExceeded = computed(() =>
  props.monthlyBudget != null && props.monthlyBudget > 0 && projectedTotal.value > props.monthlyBudget,
);

const budgetRemaining = computed(() => {
  if (props.monthlyBudget == null || props.monthlyBudget <= 0) return null;
  return props.monthlyBudget - projectedTotal.value;
});

const checkedItems = computed(() =>
  props.modelValue.filter((item) => checkedItemIds.value.has(item.uid)),
);

function removeItem(uid) {
  emit('update:modelValue', props.modelValue.filter((item) => item.uid !== uid));
}

function clearAll() {
  emit('update:modelValue', []);
}

function addSelectedPlan() {
  if (!selectedPlan.value) return;
  emit('add-plan', buildCalcItemFromPlan(selectedPlan.value));
}

function subscriptionUrlFor(item) {
  if (!item?.platform_id) return '';
  return platformWebsiteById.value.get(String(item.platform_id)) || '';
}

function isChecked(item) {
  return checkedItemIds.value.has(item.uid);
}

function canCheckItem(item) {
  return item?.platform_id && item?.plan_id && !subscriptionSaver.isExisting(item);
}

function toggleCheckedItem(item, checked) {
  const nextIds = new Set(checkedItemIds.value);
  if (checked) {
    nextIds.add(item.uid);
  } else {
    nextIds.delete(item.uid);
  }
  checkedItemIds.value = nextIds;
}

async function saveCheckedItems() {
  const saved = await subscriptionSaver.saveCalcItems(checkedItems.value);
  if (!saved.length) return;
  const savedPlatformIds = new Set(saved.map((item) => String(item.platform)));
  checkedItemIds.value = new Set(
    [...checkedItemIds.value].filter((uid) => {
      const calcItem = props.modelValue.find((item) => item.uid === uid);
      return calcItem && !savedPlatformIds.has(String(calcItem.platform_id));
    }),
  );
}

function onDragOver(event) {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'copy';
}

function onDrop(event) {
  event.preventDefault();
  const raw = event.dataTransfer.getData('application/json');
  if (!raw) return;
  try {
    const plan = JSON.parse(raw);
    emit('drop-plan', plan);
  } catch {
    /* ignore invalid payload */
  }
}

onMounted(() => {
  loadPlans();
  subscriptionSaver.loadExistingSubscriptions();
});

defineExpose({ budgetExceeded, projectedTotal, calcTotal });
</script>

<template>
  <section
    class="calc-panel panel"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <div class="calc-head">
      <h2>구독 계산기</h2>
      <button v-if="modelValue.length" class="button" type="button" @click="clearAll">비우기</button>
    </div>
    <p class="muted small">OTT와 요금제를 직접 고르거나, 추천 리포트의 요금제를 드래그하세요.</p>

    <div class="plan-picker">
      <div class="field">
        <label for="calc-platform">OTT</label>
        <select id="calc-platform" v-model="selectedPlatformId" :disabled="plansLoading">
          <option value="">OTT 선택</option>
          <option v-for="platform in platforms" :key="platform.id" :value="platform.id">
            {{ platform.name }}
          </option>
        </select>
      </div>

      <div class="field">
        <label for="calc-plan">요금제</label>
        <select
          id="calc-plan"
          v-model="selectedPlanId"
          :disabled="!selectedPlatformId || plansLoading"
        >
          <option value="">요금제 선택</option>
          <option v-for="plan in filteredPlans" :key="plan.id" :value="plan.id">
            {{ plan.plan_name }} · {{ formatWon(plan.price) }}원 · {{ billingLabel(plan.billing_period) }}
          </option>
        </select>
      </div>

      <button
        type="button"
        class="button primary add-plan-btn"
        :disabled="!selectedPlan"
        @click="addSelectedPlan"
      >
        추가
      </button>
    </div>

    <p v-if="plansError" class="picker-error">
      요금제 목록을 불러오지 못했습니다.
    </p>
    <p v-else-if="selectedPlan" class="selected-plan-hint muted small">
      월 {{ formatWon(planMonthlyPrice(selectedPlan)) }}원으로 계산됩니다.
    </p>
    <p v-if="subscriptionSaver.error.value" class="save-feedback error">
      {{ subscriptionSaver.error.value }}
    </p>
    <p v-else-if="subscriptionSaver.success.value" class="save-feedback success">
      {{ subscriptionSaver.success.value }}
    </p>

    <ul v-if="modelValue.length" class="calc-list">
      <li
        v-for="item in modelValue"
        :key="item.uid"
        :class="{ disabled: !canCheckItem(item) }"
        @click="canCheckItem(item) && !subscriptionSaver.isBusy.value && toggleCheckedItem(item, !isChecked(item))"
      >
        <label class="item-check" :class="{ disabled: !canCheckItem(item) }" @click.stop>
          <input
            type="checkbox"
            :checked="isChecked(item)"
            :disabled="!canCheckItem(item) || subscriptionSaver.isBusy.value"
            @change="toggleCheckedItem(item, $event.target.checked)"
          />
          <span class="sr-only">내 구독에 추가할 요금제 선택</span>
        </label>
        <div>
          <span v-if="item.item_type && item.item_type !== 'plan'" class="type-badge">
            {{ itemTypeLabel(item.item_type) }}
          </span>
          <strong>{{ item.platform_name }} · {{ item.plan_name }}</strong>
          <span class="muted">월 {{ formatWon(item.monthly_price) }}원 환산</span>
          <span v-if="subscriptionSaver.isExisting(item)" class="already-owned">이미 내 구독에 있음</span>
        </div>
        <div class="calc-actions">
          <a
            v-if="subscriptionUrlFor(item)"
            class="subscribe-link"
            :href="subscriptionUrlFor(item)"
            target="_blank"
            rel="noreferrer"
            @click.stop
          >
            구독하러 가기
          </a>
          <button type="button" class="remove-btn" aria-label="제거" @click.stop="removeItem(item.uid)">×</button>
        </div>
      </li>
    </ul>
    <p v-else class="empty-drop">추가한 요금제가 없습니다.</p>

    <div v-if="modelValue.length" class="bulk-save-row">
      <button
        type="button"
        class="button primary bulk-save-btn"
        :disabled="!checkedItems.length || subscriptionSaver.isBusy.value"
        @click="saveCheckedItems"
      >
        체크한 요금제 내 구독에 추가
      </button>
      <span class="muted small">{{ checkedItems.length }}개 선택됨</span>
    </div>

    <div class="calc-totals">
      <div><span>기존 구독 (월)</span><strong>{{ formatWon(existingMonthly) }}원</strong></div>
      <div><span>+ 신규 추가 (월)</span><strong>{{ formatWon(calcTotal) }}원</strong></div>
      <div class="total-row"><span>예상 월 합계</span><strong>{{ formatWon(projectedTotal) }}원</strong></div>
      <div v-if="monthlyBudget != null && monthlyBudget > 0" class="budget-row">
        <span>설정 예산</span><strong>{{ formatWon(monthlyBudget) }}원</strong>
      </div>
    </div>

    <p v-if="budgetExceeded" class="budget-warn">
      월 예산 {{ formatWon(monthlyBudget) }}원을 {{ formatWon(projectedTotal - monthlyBudget) }}원 초과합니다.
    </p>
    <p v-else-if="budgetRemaining != null && modelValue.length" class="budget-ok muted small">
      예산 대비 {{ formatWon(budgetRemaining) }}원 여유가 있습니다.
    </p>
  </section>
</template>

<style scoped>
.calc-panel {
  padding: 18px;
  margin-top: 20px;
}

.calc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.calc-head h2 {
  margin: 0;
  font-size: 18px;
}

.plan-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr) auto;
  gap: 10px;
  align-items: end;
  margin-top: 14px;
}

.plan-picker .field {
  margin: 0;
}

.plan-picker label {
  display: block;
  margin-bottom: 6px;
  color: var(--ws-muted);
  font-size: 12px;
  font-weight: 800;
}

.plan-picker select {
  width: 100%;
}

.add-plan-btn {
  min-height: 42px;
  white-space: nowrap;
}

.add-plan-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.picker-error {
  margin: 10px 0 0;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 700;
}

.selected-plan-hint {
  margin-top: 8px;
}

.calc-list {
  list-style: none;
  margin: 14px 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.calc-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
  cursor: pointer;
}

.calc-list li:hover {
  border-color: var(--ws-secondary);
}

.calc-list li.disabled {
  cursor: default;
}

.calc-list li.disabled:hover {
  border-color: var(--ws-border);
}

.item-check {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 22px;
  height: 22px;
}

.item-check input {
  width: 16px;
  height: 16px;
  accent-color: var(--ws-primary);
}

.item-check.disabled {
  opacity: 0.45;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.calc-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.save-feedback {
  margin: 10px 0 0;
  padding: 9px 11px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
}

.save-feedback.success {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}

.save-feedback.error {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.calc-list strong {
  display: block;
  font-size: 14px;
}

.subscribe-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--ws-secondary);
  border-radius: 8px;
  background: #ffffff;
  color: #141414;
  font-size: 12px;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
}

.subscribe-link:hover {
  background: var(--ws-secondary);
}

.already-owned {
  display: inline-block;
  margin-top: 7px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.type-badge {
  display: inline-block;
  margin-bottom: 2px;
  padding: 1px 6px;
  border-radius: 999px;
  background: #ede9fe;
  color: #6d28d9;
  font-size: 10px;
  font-weight: 800;
}

.remove-btn {
  border: none;
  background: none;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: var(--ws-muted);
}

.empty-drop {
  margin: 16px 0;
  padding: 24px;
  border: 2px dashed var(--ws-border);
  border-radius: 12px;
  text-align: center;
  color: var(--ws-muted);
  font-size: 14px;
}

.bulk-save-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.bulk-save-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.calc-totals {
  display: grid;
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--ws-border);
}

.calc-totals div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
}

.total-row {
  font-size: 16px;
  padding-top: 6px;
}

.budget-row {
  color: var(--ws-muted);
}

.budget-warn {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 14px;
  font-weight: 600;
}

.budget-ok {
  margin-top: 10px;
}

@media (max-width: 640px) {
  .plan-picker {
    grid-template-columns: 1fr;
  }

  .calc-list li {
    align-items: stretch;
    flex-direction: column;
  }

  .calc-actions {
    justify-content: space-between;
  }
}
</style>
