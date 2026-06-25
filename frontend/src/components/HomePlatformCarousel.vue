<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import ContentCard from './ContentCard.vue';

const props = defineProps({
  groups: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(['open']);
const activeIndex = ref(0);
const autoplayTimer = ref(null);
const activeGroup = computed(() => props.groups[activeIndex.value] || props.groups[0] || null);
const visibleItems = computed(() => (activeGroup.value?.items || []).slice(0, 4));

function stopAutoplay() {
  if (!autoplayTimer.value) return;
  clearInterval(autoplayTimer.value);
  autoplayTimer.value = null;
}

function selectSlide(index) {
  if (!props.groups.length) return;
  activeIndex.value = (index + props.groups.length) % props.groups.length;
}

function moveSlide(direction) {
  selectSlide(activeIndex.value + direction);
}

function startAutoplay() {
  stopAutoplay();
  if (props.groups.length <= 1) return;
  autoplayTimer.value = setInterval(() => {
    moveSlide(1);
  }, 4200);
}

watch(() => props.groups.length, () => {
  activeIndex.value = 0;
  startAutoplay();
});

onMounted(startAutoplay);
onBeforeUnmount(stopAutoplay);
</script>

<template>
  <section
    v-if="activeGroup"
    class="platform-carousel"
    @mouseenter="stopAutoplay"
    @mouseleave="startAutoplay"
    @focusin="stopAutoplay"
    @focusout="startAutoplay"
  >
      <header class="platform-carousel-head">
        <div class="platform-title">
          <img v-if="activeGroup.icon_url" :src="activeGroup.icon_url" :alt="activeGroup.name" />
          <span v-else class="platform-fallback">{{ activeGroup.name?.charAt(0) }}</span>
          <div>
            <p class="rank-label">추천 {{ activeIndex + 1 }}위</p>
            <h3>{{ activeGroup.name }}</h3>
            <p class="muted">{{ activeGroup.title_count }}편</p>
          </div>
        </div>
        <div class="carousel-controls" aria-label="작품 캐러셀 이동">
          <button class="icon-button" type="button" aria-label="이전 OTT" @click="moveSlide(-1)">
            ‹
          </button>
          <button class="icon-button" type="button" aria-label="다음 OTT" @click="moveSlide(1)">
            ›
          </button>
        </div>
      </header>

      <div class="platform-title-strip">
        <ContentCard
          v-for="item in visibleItems"
          :key="`${item.media_type}-${item.tmdb_id}`"
          class="carousel-card"
          :item="item"
          :compact="true"
          :media-type="item.media_type"
          @open="emit('open', item)"
        />
      </div>

      <div class="slide-dots" aria-label="추천 OTT 선택">
        <button
          v-for="(group, index) in groups"
          :key="group.platform_id"
          class="slide-dot"
          :class="{ active: index === activeIndex }"
          type="button"
          :aria-label="`${group.name} 보기`"
          @click="selectSlide(index)"
        />
      </div>
    </section>
</template>

<style scoped>
.platform-carousel {
  display: grid;
  gap: 14px;
}

.platform-carousel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.platform-title {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;
}

.platform-title img,
.platform-fallback {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: #fff;
  color: #26323d;
  font-size: 16px;
  font-weight: 900;
  object-fit: contain;
}

.platform-title h3 {
  overflow: hidden;
  font-size: 19px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.platform-title p {
  margin: 2px 0 0;
  font-size: 12px;
}

.rank-label {
  margin: 0 0 2px;
  color: var(--ws-primary);
  font-size: 12px;
  font-weight: 900;
}

.carousel-controls {
  display: flex;
  gap: 6px;
}

.icon-button {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
  cursor: pointer;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.icon-button:hover {
  border-color: var(--ws-primary);
  color: var(--ws-primary);
}

.carousel-card {
  min-width: 0;
}

.platform-title-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.carousel-card :deep(.card-body) {
  padding: 10px;
}

.carousel-card :deep(.card-body h2) {
  font-size: 14px;
  line-height: 1.35;
}

.carousel-card :deep(.reaction-icon-button) {
  width: 36px;
  height: 32px;
}

@media (min-width: 1080px) {
  .platform-title-strip {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .carousel-card :deep(.card-body h2) {
    font-size: 14px;
  }
}

@media (max-width: 640px) {
  .platform-title-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
}

.slide-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.slide-dot {
  width: 28px;
  height: 8px;
  border: 0;
  border-radius: 999px;
  background: var(--ws-border);
  cursor: pointer;
}

.slide-dot.active {
  background: var(--ws-primary);
}

@media (max-width: 620px) {
  .platform-carousel-head {
    align-items: flex-start;
  }
}
</style>
