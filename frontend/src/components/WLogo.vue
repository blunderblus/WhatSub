<script setup>
defineProps({
  size: { type: Number, default: 38 },
});
</script>

<template>
  <img
    class="w-logo"
    src="/img/brand-icon.png"
    alt=""
    aria-hidden="true"
    :style="{ width: `${size}px`, height: `${size}px` }"
  />
</template>

<style scoped>
.w-logo {
  display: block;
  border-radius: 8px;
  object-fit: cover;
}
</style>
