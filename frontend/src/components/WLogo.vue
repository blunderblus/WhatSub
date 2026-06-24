<script setup>
defineProps({
  size: { type: Number, default: 38 },
});
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 38 38" fill="none" aria-hidden="true">
    <defs>
      <linearGradient id="wt1" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#FCA311" />
        <stop offset="100%" stop-color="#e07a00" stop-opacity="0.85" />
      </linearGradient>
      <linearGradient id="wt2" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#FCA311" stop-opacity="0.95" />
        <stop offset="100%" stop-color="#D9DD92" stop-opacity="0.9" />
      </linearGradient>
      <linearGradient id="wt3" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#D9DD92" />
        <stop offset="100%" stop-color="#a0d020" stop-opacity="0.85" />
      </linearGradient>
    </defs>
    <g transform="rotate(-22 13 22)">
      <rect x="5" y="3" width="16" height="27" rx="4" fill="url(#wt1)" />
    </g>
    <g transform="rotate(-4 19 22)">
      <rect x="11" y="1" width="16" height="30" rx="4" fill="url(#wt2)" />
    </g>
    <g transform="rotate(18 25 22)">
      <rect x="17" y="3" width="16" height="27" rx="4" fill="url(#wt3)" />
    </g>
  </svg>
</template>
