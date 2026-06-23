<script setup>
import { computed } from 'vue';
import { formatWon, itemTypeLabel } from '../utils/billing';

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

const emit = defineEmits(['update:modelValue', 'drop-plan']);

const calcTotal = computed(() =>
  props.modelValue.reduce((sum, item) => sum + Number(item.monthly_price || 0), 0),
);

const projectedTotal = computed(() => props.existingMonthly + calcTotal.value);

const budgetExceeded = computed(() =>
  props.monthlyBudget != null && props.monthlyBudget > 0 && projectedTotal.value > props.monthlyBudget,
);

const budgetRemaining = computed(() => {
  if (props.monthlyBudget == null || props.monthlyBudget <= 0) return null;
  return props.monthlyBudget - projectedTotal.value;
});

function removeItem(uid) {
  emit('update:modelValue', props.modelValue.filter((item) => item.uid !== uid));
}

function clearAll() {
  emit('update:modelValue', []);
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
    <p class="muted small">신규로 추가할 요금제를 클릭하거나 이 영역으로 드래그하세요.</p>

    <ul v-if="modelValue.length" class="calc-list">
      <li v-for="item in modelValue" :key="item.uid">
        <div>
          <span v-if="item.item_type && item.item_type !== 'plan'" class="type-badge">
            {{ itemTypeLabel(item.item_type) }}
          </span>
          <strong>{{ item.platform_name }} · {{ item.plan_name }}</strong>
          <span class="muted">월 {{ formatWon(item.monthly_price) }}원 환산</span>
        </div>
        <button type="button" class="remove-btn" aria-label="제거" @click="removeItem(item.uid)">×</button>
      </li>
    </ul>
    <p v-else class="empty-drop">추가한 요금제가 없습니다.</p>

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
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: var(--ws-surface-2);
}

.calc-list strong {
  display: block;
  font-size: 14px;
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
</style>
