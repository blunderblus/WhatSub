<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
  scheduleItems: {
    type: Array,
    default: () => [],
  },
  subscriptions: {
    type: Array,
    default: () => [],
  },
  highlightSubscriptionId: {
    type: [Number, String, null],
    default: null,
  },
});

const emit = defineEmits(['select-subscription']);

const viewDate = ref(new Date());

const year = computed(() => viewDate.value.getFullYear());
const month = computed(() => viewDate.value.getMonth());

const monthLabel = computed(() =>
  viewDate.value.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' }),
);

const weekdayLabels = ['일', '월', '화', '수', '목', '금', '토'];

function isoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

function maxDate(a, b) {
  return a >= b ? a : b;
}

function minDate(a, b) {
  return a <= b ? a : b;
}

const itemsByDate = computed(() => {
  const map = {};
  for (const item of props.scheduleItems) {
    if (!item.date) continue;
    map[item.date] = map[item.date] || [];
    map[item.date].push(item);
  }
  return map;
});

const highlightSub = computed(() =>
  props.subscriptions.find((sub) => String(sub.id) === String(props.highlightSubscriptionId)) || null,
);

function isHighlightedRemaining(dateKey) {
  if (!highlightSub.value) return false;
  const sub = highlightSub.value;
  const todayKey = isoDate(new Date());
  const monthStart = isoDate(new Date(year.value, month.value, 1));
  const monthEnd = isoDate(new Date(year.value, month.value + 1, 0));
  const periodEnd = sub.period_end || sub.next_payment_date || sub.renewal_date;
  if (!periodEnd) return false;
  const remainingStart = maxDate(todayKey, monthStart);
  const remainingEnd = minDate(periodEnd, monthEnd);
  return dateKey >= remainingStart && dateKey <= remainingEnd;
}

function isInSubscriptionPeriod(dateKey) {
  if (highlightSub.value) return false;
  return props.subscriptions.some((sub) => {
    const start = sub.period_start || sub.last_payment_date;
    const end = sub.period_end || sub.next_payment_date || sub.renewal_date;
    if (!start || !end) return false;
    return dateKey >= start && dateKey <= end;
  });
}

const calendarCells = computed(() => {
  const first = new Date(year.value, month.value, 1);
  const startOffset = first.getDay();
  const daysInMonth = new Date(year.value, month.value + 1, 0).getDate();
  const cells = [];
  const todayKey = isoDate(new Date());

  for (let i = 0; i < startOffset; i += 1) {
    cells.push({ empty: true, key: `e-${i}` });
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = new Date(year.value, month.value, day);
    const key = isoDate(date);
    cells.push({
      empty: false,
      key,
      day,
      date: key,
      items: itemsByDate.value[key] || [],
      isToday: key === todayKey,
      inPeriod: isInSubscriptionPeriod(key),
      highlighted: isHighlightedRemaining(key),
    });
  }
  return cells;
});

const activePeriods = computed(() =>
  props.subscriptions.filter((sub) => sub.period_start && sub.period_end),
);

watch(
  () => props.highlightSubscriptionId,
  (id) => {
    if (!id) return;
    const sub = props.subscriptions.find((s) => String(s.id) === String(id));
    const anchor = sub?.period_end || sub?.next_payment_date || sub?.renewal_date;
    if (anchor) {
      const d = new Date(anchor);
      viewDate.value = new Date(d.getFullYear(), d.getMonth(), 1);
    }
  },
);

function prevMonth() {
  viewDate.value = new Date(year.value, month.value - 1, 1);
}

function nextMonth() {
  viewDate.value = new Date(year.value, month.value + 1, 1);
}

function formatDuration(start, end) {
  if (!start || !end) return '-';
  const days = Math.round((new Date(end) - new Date(start)) / (1000 * 60 * 60 * 24));
  if (days >= 365) return `${Math.round(days / 365)}년`;
  if (days >= 30) return `${Math.round(days / 30)}개월`;
  return `${days}일`;
}

function formatDisplayDate(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' });
}

function toggleHighlight(subId) {
  const next = String(props.highlightSubscriptionId) === String(subId) ? null : subId;
  emit('select-subscription', next);
}
</script>

<template>
  <div class="calendar-wrap">
    <p v-if="highlightSub" class="highlight-banner">
      <strong>{{ highlightSub.platform_name }}</strong> 이번 달 잔여 구독 기간이 강조 표시됩니다.
    </p>

    <div class="cal-head">
      <button type="button" class="nav-btn" aria-label="이전 달" @click="prevMonth">‹</button>
      <strong>{{ monthLabel }}</strong>
      <button type="button" class="nav-btn" aria-label="다음 달" @click="nextMonth">›</button>
    </div>

    <div class="weekdays">
      <span v-for="w in weekdayLabels" :key="w">{{ w }}</span>
    </div>

    <div class="grid">
      <div
        v-for="cell in calendarCells"
        :key="cell.key"
        class="cell"
        :class="{
          empty: cell.empty,
          today: cell.isToday,
          inPeriod: cell.inPeriod,
          highlighted: cell.highlighted,
          hasItems: cell.items?.length,
        }"
      >
        <template v-if="!cell.empty">
          <span class="day-num">{{ cell.day }}</span>
          <div v-if="cell.items.length" class="event-list">
            <div
              v-for="item in cell.items.slice(0, 3)"
              :key="item.id"
              class="event-chip"
              :class="item.event_type"
            >
              {{ item.platform_name }}: {{ formatMoney(item.amount) }}원 {{ item.status_label }}
            </div>
            <div v-if="cell.items.length > 3" class="event-more">+{{ cell.items.length - 3 }}건</div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="activePeriods.length" class="period-list">
      <h4>구독 기간 (결제 주기 기준)</h4>
      <p class="period-hint">항목을 클릭하면 캘린더에 이번 달 잔여 기간이 표시됩니다.</p>
      <ul>
        <li
          v-for="sub in activePeriods"
          :key="`period-${sub.id}`"
          role="button"
          tabindex="0"
          :class="{ active: String(sub.id) === String(highlightSubscriptionId) }"
          @click="toggleHighlight(sub.id)"
          @keydown.enter="toggleHighlight(sub.id)"
        >
          <strong>{{ sub.platform_name }}</strong>
          <span>{{ sub.plan_name }}</span>
          <span class="period-range">
            {{ formatDisplayDate(sub.period_start) }} ~ {{ formatDisplayDate(sub.period_end) }}
            · {{ formatDuration(sub.period_start, sub.period_end) }}
          </span>
          <span v-if="sub.last_payment_date" class="payment-meta">
            최근 결제 {{ formatDisplayDate(sub.last_payment_date) }}
            · 다음 결제 {{ formatDisplayDate(sub.next_payment_date || sub.period_end) }}
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.calendar-wrap {
  display: grid;
  gap: 16px;
}

.highlight-banner {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #1e3a8a;
  color: #bfdbfe;
  font-size: 13px;
}

.cal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.nav-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #475569;
  border-radius: 8px;
  background: #1e293b;
  color: #f8fafc;
  cursor: pointer;
  font-size: 18px;
}

.weekdays,
.grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 6px;
}

.weekdays span {
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  font-weight: 700;
}

.cell {
  min-height: 96px;
  padding: 6px;
  border: 1px solid #475569;
  border-radius: 10px;
  background: #1e293b;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
}

.cell.empty {
  background: transparent;
  border-color: transparent;
}

.cell.today .day-num {
  color: #38bdf8;
}

.cell.today {
  border-color: #38bdf8;
}

.cell.inPeriod:not(.hasItems):not(.highlighted) {
  background: #172554;
}

.cell.highlighted {
  background: #312e81;
  border-color: #818cf8;
  box-shadow: inset 0 0 0 1px rgba(129, 140, 248, 0.45);
}

.cell.hasItems {
  background: #0f172a;
}

.day-num {
  font-size: 13px;
  font-weight: 800;
  color: #f8fafc;
  line-height: 1.2;
}

.event-list {
  display: grid;
  gap: 3px;
  flex: 1;
}

.event-chip {
  padding: 3px 5px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.3;
  word-break: keep-all;
  overflow: hidden;
}

.event-chip.payment {
  background: #14532d;
  color: #bbf7d0;
}

.event-chip.renewal {
  background: #78350f;
  color: #fde68a;
}

.event-more {
  font-size: 10px;
  color: #94a3b8;
}

.period-list h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: #e2e8f0;
}

.period-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #94a3b8;
}

.period-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.period-list li {
  padding: 10px 12px;
  border: 1px solid #334155;
  border-radius: 8px;
  background: #1e293b;
  font-size: 13px;
  color: #e2e8f0;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.period-list li:hover {
  border-color: #818cf8;
}

.period-list li.active {
  border-color: #818cf8;
  background: #312e81;
}

.period-list strong {
  display: block;
  color: #f8fafc;
}

.period-list span {
  display: block;
  color: #94a3b8;
  font-size: 12px;
  margin-top: 2px;
}

.period-range,
.payment-meta {
  color: #cbd5e1 !important;
  font-weight: 600;
}
</style>
