<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['open']);
</script>

<template>
  <article
    class="content-card"
    tabindex="0"
    @click="emit('open', item)"
    @keydown.enter="emit('open', item)"
  >
    <img v-if="item.poster_url" class="poster" :src="item.poster_url" :alt="item.title" loading="lazy" />
    <div v-else class="poster-empty">{{ item.title }}</div>
    <div class="card-body">
      <div v-if="!compact" class="meta-line">
        <span>{{ item.release_date || '공개일 미정' }}</span>
        <strong v-if="item.rating !== undefined">{{ Number(item.rating).toFixed(1) }}</strong>
      </div>
      <h2>{{ item.title }}</h2>
      <p v-if="!compact && item.overview" class="muted">{{ item.overview }}</p>
      <span v-if="compact && item.media_type" class="muted">
        {{ item.media_type === 'tv' ? '시리즈' : '영화' }} · {{ item.release_date || '공개일 미정' }}
      </span>
    </div>
  </article>
</template>

<style scoped>
.meta-line {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #667586;
  font-size: 13px;
  font-weight: 700;
}

.meta-line strong {
  color: #b24d18;
}

.card-body h2 {
  font-size: 16px;
}

.card-body p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  min-height: 67px;
  margin: 0;
}
</style>
