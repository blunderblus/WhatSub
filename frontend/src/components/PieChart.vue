<script setup>
import { computed } from 'vue';

const props = defineProps({
  segments: {
    type: Array,
    default: () => [],
    // [{ label, value, color? }]
  },
  size: {
    type: Number,
    default: 200,
  },
  donut: {
    type: Boolean,
    default: true,
  },
});

const PALETTE = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f97316', '#eab308',
  '#D9DD92', '#14b8a6', '#0ea5e9', '#64748b', '#a855f7',
];

const total = computed(() =>
  props.segments.reduce((sum, s) => sum + Number(s.value || 0), 0),
);

const slices = computed(() => {
  if (!total.value) return [];
  let angle = -90;
  return props.segments.map((seg, i) => {
    const value = Number(seg.value || 0);
    const pct = value / total.value;
    const sweep = pct * 360;
    const start = angle;
    angle += sweep;
    return {
      ...seg,
      pct,
      start,
      sweep,
      color: seg.color || PALETTE[i % PALETTE.length],
    };
  });
});

function polar(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function arcPath(slice) {
  const cx = 100;
  const cy = 100;
  const r = 96;
  const ir = props.donut ? r * 0.55 : 0;
  if (slice.sweep >= 359.99) {
    return [
      `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r}`,
      props.donut ? `M ${cx} ${cy - ir} A ${ir} ${ir} 0 1 0 ${cx + 0.01} ${cy - ir} Z` : '',
    ].filter(Boolean).join(' ');
  }
  const [x1, y1] = polar(cx, cy, r, slice.start);
  const [x2, y2] = polar(cx, cy, r, slice.start + slice.sweep);
  const large = slice.sweep > 180 ? 1 : 0;
  if (!props.donut) {
    return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
  }
  const [ix1, iy1] = polar(cx, cy, ir, slice.start + slice.sweep);
  const [ix2, iy2] = polar(cx, cy, ir, slice.start);
  return [
    `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`,
    `L ${ix1} ${iy1} A ${ir} ${ir} 0 ${large} 0 ${ix2} ${iy2} Z`,
  ].join(' ');
}
</script>

<template>
  <div class="pie-wrap">
    <svg :width="size" :height="size" viewBox="0 0 200 200" class="pie-svg" :style="{ width: `${size}px`, height: `${size}px` }">
      <g v-if="!total">
        <circle cx="100" cy="100" r="96" fill="var(--ws-border)" />
      </g>
      <path
        v-for="(slice, i) in slices"
        :key="i"
        :d="arcPath(slice)"
        :fill="slice.color"
        stroke="var(--ws-surface)"
        stroke-width="1.5"
      />
    </svg>
    <ul v-if="segments.length" class="legend">
      <li v-for="(slice, i) in slices" :key="`leg-${i}`">
        <span class="dot" :style="{ background: slice.color }"></span>
        <span class="label">{{ slice.label }}</span>
        <span class="pct">{{ Math.round(slice.pct * 100) }}%</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.pie-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

.pie-svg {
  flex: none;
}

.legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
  min-width: 140px;
  font-size: 13px;
}

.legend li {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  gap: 8px;
  align-items: center;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pct {
  color: var(--ws-muted);
  font-variant-numeric: tabular-nums;
}
</style>
