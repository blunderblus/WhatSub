<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import {
  buildChartYScale,
  buildFocusMonthStats,
  buildPaymentFlowDailySeries,
  buildPaymentFlowSeries,
  buildPaymentFlowWeeklySeries,
  formatWon,
} from '../utils/billing';

const props = defineProps({
  scheduleItems: {
    type: Array,
    default: () => [],
  },
  budget: {
    type: Number,
    default: null,
  },
  monthlyEstimate: {
    type: Number,
    default: 0,
  },
});

const viewMode = ref('month');
const focusMonthKey = ref(currentMonthKey());
const lineRef = ref(null);
const drawKey = ref(0);
const pathLength = ref(1000);
const hoveredIndex = ref(null);

const WIDTH = 720;
const HEIGHT = 300;
const PAD = { top: 28, right: 132, bottom: 40, left: 58 };
const BADGE_H = 24;
const BADGE_W = 120;
const BADGE_GAP = 10;

const plotWidth = WIDTH - PAD.left - PAD.right;
const plotHeight = HEIGHT - PAD.top - PAD.bottom;

function currentMonthKey(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

function shiftFocusMonth(delta) {
  const [year, month] = focusMonthKey.value.split('-').map(Number);
  const next = new Date(year, month - 1 + delta, 1);
  focusMonthKey.value = currentMonthKey(next);
}

const focusMonthLabel = computed(() => {
  const [year, month] = focusMonthKey.value.split('-').map(Number);
  return `${year}년 ${month}월`;
});

const showMonthlyGuides = computed(() => viewMode.value === 'month');

const points = computed(() => {
  if (viewMode.value === 'day') {
    return buildPaymentFlowDailySeries(props.scheduleItems, focusMonthKey.value);
  }
  if (viewMode.value === 'week') {
    return buildPaymentFlowWeeklySeries(props.scheduleItems, focusMonthKey.value);
  }
  return buildPaymentFlowSeries(props.scheduleItems);
});

const focusMonthStats = computed(() => (
  viewMode.value === 'month'
    ? null
    : buildFocusMonthStats(props.scheduleItems, focusMonthKey.value)
));

const activePeriodPoints = computed(() => points.value.filter((point) => point.amount > 0));

const yScale = computed(() => buildChartYScale(
  points.value.map((point) => point.amount),
  showMonthlyGuides.value ? props.budget : null,
  showMonthlyGuides.value ? props.monthlyEstimate : 0,
  { includeGuides: showMonthlyGuides.value },
));

const maxY = computed(() => yScale.value.maxY);
const yTicks = computed(() => yScale.value.ticks);

const numericBudget = computed(() => Number(props.budget || 0));
const numericEstimate = computed(() => Number(props.monthlyEstimate || 0));

function xAt(index) {
  const count = Math.max(points.value.length - 1, 1);
  return PAD.left + (index / count) * plotWidth;
}

function yAt(value) {
  return PAD.top + plotHeight - (Number(value || 0) / maxY.value) * plotHeight;
}

const linePath = computed(() => {
  if (!points.value.length) return '';
  return points.value
    .map((point, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i).toFixed(2)} ${yAt(point.amount).toFixed(2)}`)
    .join(' ');
});

const areaPath = computed(() => {
  if (!points.value.length) return '';
  const baseline = yAt(0).toFixed(2);
  const top = points.value
    .map((point, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i).toFixed(2)} ${yAt(point.amount).toFixed(2)}`)
    .join(' ');
  const lastX = xAt(points.value.length - 1).toFixed(2);
  const firstX = xAt(0).toFixed(2);
  return `${top} L ${lastX} ${baseline} L ${firstX} ${baseline} Z`;
});

const budgetY = computed(() => (
  showMonthlyGuides.value && numericBudget.value > 0 ? yAt(numericBudget.value) : null
));
const estimateY = computed(() => (
  showMonthlyGuides.value && numericEstimate.value > 0 ? yAt(numericEstimate.value) : null
));

function resolveBadgePositions(entries) {
  const minCenter = PAD.top + BADGE_H / 2;
  const maxCenter = PAD.top + plotHeight - BADGE_H / 2;
  const badges = entries
    .map((entry) => ({
      ...entry,
      centerY: Math.min(Math.max(entry.lineY, minCenter), maxCenter),
    }))
    .sort((a, b) => a.centerY - b.centerY);

  for (let i = 1; i < badges.length; i += 1) {
    const minY = badges[i - 1].centerY + BADGE_H + BADGE_GAP;
    if (badges[i].centerY < minY) badges[i].centerY = minY;
  }

  const last = badges[badges.length - 1];
  if (last && last.centerY > maxCenter) {
    const shift = last.centerY - maxCenter;
    badges.forEach((badge) => {
      badge.centerY -= shift;
    });
  }

  for (let i = badges.length - 2; i >= 0; i -= 1) {
    const maxY = badges[i + 1].centerY - BADGE_H - BADGE_GAP;
    if (badges[i].centerY > maxY) badges[i].centerY = maxY;
  }

  badges.forEach((badge) => {
    badge.centerY = Math.max(badge.centerY, minCenter);
  });

  return badges;
}

const referenceBadges = computed(() => {
  const entries = [];
  if (estimateY.value != null) {
    entries.push({
      id: 'estimate',
      lineY: estimateY.value,
      text: `월 예상 ${formatWon(numericEstimate.value)}원`,
      kind: 'estimate',
    });
  }
  if (budgetY.value != null) {
    entries.push({
      id: 'budget',
      lineY: budgetY.value,
      text: `예산 ${formatWon(numericBudget.value)}원`,
      kind: 'budget',
    });
  }
  return resolveBadgePositions(entries);
});

const overBudgetCount = computed(() => {
  if (!showMonthlyGuides.value || numericBudget.value <= 0) return 0;
  return points.value.filter((point) => point.amount > numericBudget.value).length;
});

const chartSummary = computed(() => {
  const budgetText = numericBudget.value > 0 ? `예산 ${formatWon(numericBudget.value)}원` : '예산 미설정';
  return `결제 흐름 차트. ${budgetText}`;
});

const viewModeLabel = computed(() => {
  if (viewMode.value === 'day') return '일별 결제';
  if (viewMode.value === 'week') return '주별 결제';
  return '월별 결제';
});

const periodSummaryText = computed(() => {
  if (!focusMonthStats.value) return '';
  const stats = focusMonthStats.value;
  const unit = viewMode.value === 'day' ? '일별' : '주별';
  const activeCount = activePeriodPoints.value.length;
  return `${focusMonthLabel.value} ${unit} 차트 · 결제 ${stats.paymentCount}건 · `
    + `활성 ${unit.replace('별', '')} ${activeCount}개 · `
    + `합계 ${formatWon(stats.total)}원 `
    + `(완료 ${formatWon(stats.paidTotal)}원 / 예정 ${formatWon(stats.scheduledTotal)}원)`;
});

function shouldShowXLabel(index) {
  if (viewMode.value !== 'day') return true;
  const total = points.value.length;
  if (total <= 12) return true;
  const step = total > 28 ? 5 : 3;
  return index === 0 || index === total - 1 || (index + 1) % step === 0;
}

function formatAxisWon(value) {
  if (value >= 10000) return `${Math.round(value / 10000)}만`;
  if (value >= 1000) return `${Math.round(value / 1000)}천`;
  return String(value);
}

const hoveredPoint = computed(() => (
  hoveredIndex.value != null ? points.value[hoveredIndex.value] : null
));

function periodHeading(point) {
  if (viewMode.value === 'month') return point.label;
  if (viewMode.value === 'day') return `${focusMonthLabel.value} ${point.label}일`;
  return `${focusMonthLabel.value} ${point.label}`;
}

const tooltipStyle = computed(() => {
  if (hoveredIndex.value == null || !points.value[hoveredIndex.value]) return {};
  const i = hoveredIndex.value;
  const point = points.value[i];
  const xPct = (xAt(i) / WIDTH) * 100;
  const yPct = (yAt(point.amount) / HEIGHT) * 100;
  const flipBelow = yPct < 38;
  return {
    left: `${xPct}%`,
    top: `${yPct}%`,
    transform: flipBelow ? 'translate(-50%, 14px)' : 'translate(-50%, calc(-100% - 14px))',
  };
});

function setHoveredIndex(index) {
  hoveredIndex.value = index;
}

function clearHoveredIndex() {
  hoveredIndex.value = null;
}

async function measurePath() {
  await nextTick();
  const len = lineRef.value?.getTotalLength?.() || 1000;
  pathLength.value = Math.max(len, 1);
}

watch([viewMode, focusMonthKey, () => props.scheduleItems, linePath], () => {
  drawKey.value += 1;
  hoveredIndex.value = null;
  measurePath();
}, { deep: true, immediate: true });
</script>

<template>
  <div class="payment-flow-chart">
    <div class="chart-toolbar">
      <div class="view-toggle" role="tablist" aria-label="차트 보기 단위">
        <button
          type="button"
          role="tab"
          :class="{ active: viewMode === 'month' }"
          :aria-selected="viewMode === 'month'"
          @click="viewMode = 'month'"
        >
          월
        </button>
        <button
          type="button"
          role="tab"
          :class="{ active: viewMode === 'week' }"
          :aria-selected="viewMode === 'week'"
          @click="viewMode = 'week'"
        >
          주
        </button>
        <button
          type="button"
          role="tab"
          :class="{ active: viewMode === 'day' }"
          :aria-selected="viewMode === 'day'"
          @click="viewMode = 'day'"
        >
          일
        </button>
      </div>

      <div v-if="viewMode !== 'month'" class="month-nav">
        <button type="button" class="nav-btn" aria-label="이전 달" @click="shiftFocusMonth(-1)">‹</button>
        <span>{{ focusMonthLabel }}</span>
        <button type="button" class="nav-btn" aria-label="다음 달" @click="shiftFocusMonth(1)">›</button>
      </div>
    </div>

    <div class="chart-wrap" @mouseleave="clearHoveredIndex">
      <svg
        class="chart-svg"
        :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
        role="img"
        :aria-label="chartSummary"
        preserveAspectRatio="xMidYMid meet"
      >
      <defs>
        <linearGradient id="paymentAreaFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="rgba(var(--ws-primary-rgb), 0.34)" />
          <stop offset="100%" stop-color="rgba(var(--ws-primary-rgb), 0.02)" />
        </linearGradient>
        <pattern id="budgetHatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(255, 77, 77, 0.12)" stroke-width="4" />
        </pattern>
      </defs>

      <g class="grid-lines">
        <line
          v-for="tick in yTicks"
          :key="`grid-${tick}`"
          :x1="PAD.left"
          :x2="WIDTH - PAD.right"
          :y1="yAt(tick)"
          :y2="yAt(tick)"
        />
      </g>

      <rect
        v-if="budgetY != null"
        :x="PAD.left"
        :y="PAD.top"
        :width="plotWidth"
        :height="budgetY - PAD.top"
        fill="url(#budgetHatch)"
      />

      <text
        v-for="tick in yTicks"
        :key="`ylabel-${tick}`"
        :x="PAD.left - 8"
        :y="yAt(tick) + 4"
        class="axis-label y-label"
        text-anchor="end"
      >
        {{ formatAxisWon(tick) }}
      </text>

      <text
        v-for="(point, i) in points"
        v-show="shouldShowXLabel(i)"
        :key="`xlabel-${point.key}`"
        :x="xAt(i)"
        :y="HEIGHT - 12"
        class="axis-label x-label"
        :class="{ current: point.isCurrent, future: point.isFuture }"
        text-anchor="middle"
      >
        {{ point.label }}
      </text>

      <path
        v-if="points.length"
        :key="`area-${drawKey}`"
        :d="areaPath"
        fill="url(#paymentAreaFill)"
        class="payment-area"
      />
      <path
        v-if="points.length"
        :key="`line-${drawKey}`"
        ref="lineRef"
        :d="linePath"
        class="payment-line draw-line"
        fill="none"
        :style="{
          '--path-len': `${pathLength}`,
          animationDuration: `${Math.min(1.4, 0.45 + points.length * 0.04)}s`,
        }"
      />

      <g v-for="badge in referenceBadges" :key="badge.id">
        <line
          :x1="PAD.left"
          :x2="WIDTH - PAD.right"
          :y1="badge.lineY"
          :y2="badge.lineY"
          :class="badge.kind === 'budget' ? 'budget-line' : 'estimate-line'"
        />
        <rect
          :x="WIDTH - PAD.right + 4"
          :y="badge.centerY - BADGE_H / 2"
          :width="BADGE_W"
          :height="BADGE_H"
          rx="6"
          :class="badge.kind === 'budget' ? 'budget-badge' : 'estimate-badge'"
        />
        <text
          :x="WIDTH - PAD.right + 4 + BADGE_W / 2"
          :y="badge.centerY + 4"
          class="badge-label"
          :class="badge.kind === 'budget' ? 'budget-label' : 'estimate-label'"
          text-anchor="middle"
        >
          {{ badge.text }}
        </text>
      </g>

      <line
        v-if="hoveredIndex != null"
        class="hover-guide"
        :x1="xAt(hoveredIndex)"
        :x2="xAt(hoveredIndex)"
        :y1="PAD.top"
        :y2="PAD.top + plotHeight"
      />

      <g v-for="(point, i) in points" :key="`point-${point.key}`">
        <circle
          :cx="xAt(i)"
          :cy="yAt(point.amount)"
          r="16"
          class="hit-target"
          @mouseenter="setHoveredIndex(i)"
          @focus="setHoveredIndex(i)"
        />
        <circle
          v-if="point.amount > 0 || viewMode !== 'day'"
          :cx="xAt(i)"
          :cy="yAt(point.amount)"
          :r="hoveredIndex === i ? 7 : (point.amount > 0 ? 5 : 3)"
          class="payment-point"
          :class="{
            future: point.isFuture,
            current: point.isCurrent,
            active: hoveredIndex === i,
            over: showMonthlyGuides && numericBudget > 0 && point.amount > numericBudget,
            empty: point.amount === 0,
          }"
          :style="{ animationDelay: `${0.45 + i * 0.04}s` }"
          pointer-events="none"
        />
      </g>
      </svg>

      <div
        v-if="hoveredPoint"
        class="chart-tooltip"
        :style="tooltipStyle"
        role="tooltip"
      >
        <p class="tooltip-head">
          <strong>{{ periodHeading(hoveredPoint) }}</strong>
          <span v-if="hoveredPoint.isFuture" class="tooltip-badge">예정</span>
        </p>
        <p class="tooltip-total">
          {{ formatWon(hoveredPoint.amount) }}원
          <span v-if="hoveredPoint.amount === 0" class="muted">결제 없음</span>
        </p>
        <ul v-if="hoveredPoint.payments?.length" class="tooltip-list">
          <li v-for="(payment, idx) in hoveredPoint.payments" :key="`${hoveredPoint.key}-${idx}`">
            <span>{{ payment.platform_name }}</span>
            <strong>{{ formatWon(payment.amount) }}원</strong>
          </li>
        </ul>
        <p v-else-if="hoveredPoint.amount === 0" class="tooltip-empty muted small">
          이 구간에 예정된 결제가 없습니다.
        </p>
      </div>
    </div>

    <ul class="legend">
      <li><span class="swatch payment"></span>{{ viewModeLabel }}</li>
      <li v-if="showMonthlyGuides && numericEstimate > 0"><span class="swatch estimate"></span>월 예상 지출</li>
      <li v-if="showMonthlyGuides && numericBudget > 0"><span class="swatch budget"></span>예산 한도</li>
    </ul>

    <p v-if="periodSummaryText" class="period-summary muted small">
      {{ periodSummaryText }}
    </p>

    <p v-if="showMonthlyGuides && numericBudget > 0 && overBudgetCount" class="budget-alert">
      {{ overBudgetCount }}개월에서 결제액이 예산을 초과합니다.
    </p>
    <p v-else-if="showMonthlyGuides && !numericBudget" class="budget-hint muted small">
      <RouterLink to="/onboarding/preferences">취향 설정</RouterLink>에서 월 예산을 설정하면 차트에 기준선이 표시됩니다.
    </p>
  </div>
</template>

<style scoped>
.payment-flow-chart {
  display: grid;
  gap: 12px;
}

.chart-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.view-toggle {
  display: inline-flex;
  padding: 3px;
  border: 1px solid var(--ws-border);
  border-radius: 999px;
  background: var(--ws-surface-2);
}

.view-toggle button {
  min-width: 44px;
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--ws-muted);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.view-toggle button.active {
  background: var(--ws-primary);
  color: var(--ws-primary-fg);
}

.month-nav {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--ws-text);
  font-size: 14px;
  font-weight: 800;
}

.nav-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.chart-wrap {
  position: relative;
}

.chart-svg {
  width: 100%;
  height: auto;
  display: block;
}

.chart-tooltip {
  position: absolute;
  z-index: 5;
  min-width: 168px;
  max-width: 240px;
  padding: 10px 12px;
  border: 1px solid var(--ws-border);
  border-radius: 10px;
  background: rgba(12, 18, 32, 0.96);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
  pointer-events: none;
}

.tooltip-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 6px;
  color: var(--ws-text);
  font-size: 13px;
  font-weight: 800;
}

.tooltip-badge {
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(var(--ws-primary-rgb), 0.18);
  color: var(--ws-primary);
  font-size: 11px;
  font-weight: 800;
}

.tooltip-total {
  margin: 0 0 8px;
  color: var(--ws-primary);
  font-size: 18px;
  font-weight: 900;
}

.tooltip-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
  border-top: 1px solid var(--ws-border);
  padding-top: 8px;
}

.tooltip-list li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ws-muted);
}

.tooltip-list strong {
  color: var(--ws-text);
  font-weight: 900;
  white-space: nowrap;
}

.tooltip-empty {
  margin: 0;
}

.hover-guide {
  stroke: rgba(var(--ws-primary-rgb), 0.35);
  stroke-width: 1;
  stroke-dasharray: 4 4;
  pointer-events: none;
}

.hit-target {
  fill: transparent;
  cursor: pointer;
}

.payment-point.active {
  stroke: var(--ws-primary);
  stroke-width: 3;
}

.grid-lines line {
  stroke: rgba(var(--ws-secondary-rgb), 0.14);
  stroke-width: 1;
}

.axis-label {
  fill: var(--ws-muted);
  font-size: 11px;
  font-weight: 700;
}

.x-label.current {
  fill: var(--ws-primary);
  font-weight: 900;
}

.x-label.future {
  fill: rgba(var(--ws-muted), 0.72);
}

.payment-area {
  opacity: 0;
  animation: payment-area-in 0.5s ease forwards;
}

.payment-line {
  stroke: var(--ws-primary);
  stroke-width: 2.5;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.payment-line.draw-line {
  stroke-dasharray: var(--path-len);
  stroke-dashoffset: var(--path-len);
  animation-name: payment-line-draw;
  animation-timing-function: ease;
  animation-fill-mode: forwards;
}

@keyframes payment-line-draw {
  to { stroke-dashoffset: 0; }
}

@keyframes payment-area-in {
  to { opacity: 1; }
}

.estimate-line {
  stroke: var(--ws-secondary);
  stroke-width: 2;
  stroke-dasharray: 6 5;
}

.budget-line {
  stroke: var(--ws-destructive);
  stroke-width: 2.5;
  stroke-dasharray: 8 5;
}

.estimate-badge {
  fill: rgba(var(--ws-secondary-rgb), 0.18);
  stroke: rgba(var(--ws-secondary-rgb), 0.45);
}

.budget-badge {
  fill: rgba(255, 77, 77, 0.16);
  stroke: rgba(255, 77, 77, 0.55);
}

.badge-label {
  fill: var(--ws-text);
  font-size: 10px;
  font-weight: 900;
}

.estimate-label {
  fill: var(--ws-secondary);
}

.budget-label {
  fill: #ffb4b4;
}

.payment-point {
  fill: var(--ws-primary);
  stroke: var(--ws-surface);
  stroke-width: 2;
  opacity: 0;
  animation: payment-point-in 0.25s ease forwards;
}

.payment-point.empty {
  fill: rgba(var(--ws-primary-rgb), 0.18);
}

.payment-point.future {
  fill: rgba(var(--ws-primary-rgb), 0.45);
}

.payment-point.current {
  fill: var(--ws-secondary);
}

.payment-point.over {
  fill: var(--ws-destructive);
  stroke: rgba(255, 180, 180, 0.8);
}

@keyframes payment-point-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--ws-muted);
}

.legend li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.swatch {
  width: 18px;
  height: 3px;
  border-radius: 999px;
}

.swatch.payment {
  background: var(--ws-primary);
}

.swatch.estimate {
  background: var(--ws-secondary);
  opacity: 0.85;
}

.swatch.budget {
  background: var(--ws-destructive);
  height: 2px;
  background-image: repeating-linear-gradient(
    90deg,
    var(--ws-destructive) 0 6px,
    transparent 6px 10px
  );
}

.period-summary {
  margin: 0;
}

.budget-alert {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid rgba(255, 77, 77, 0.35);
  border-radius: 8px;
  background: rgba(255, 77, 77, 0.08);
  color: #ffb4b4;
  font-size: 13px;
  font-weight: 800;
}

.budget-hint {
  margin: 0;
}

.budget-hint a {
  color: var(--ws-primary);
  font-weight: 800;
}
</style>
