<script setup>
import { useRouter } from 'vue-router';
import { useContentCard } from '../composables/useContentCard';
import { formatProviderName, providerInitial } from '../utils/formatters';

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  mediaType: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['open']);
const router = useRouter();

function promptLogin() {
  if (confirm('로그인이 필요합니다.')) {
    router.push('/login');
  }
}

const {
  visibleProviders,
  providersLoaded,
  providersLoading,
  providerError,
  reactions,
  reactionLoading,
  reactionMessage,
  scheduleProviderLoad,
  cancelProviderLoad,
  toggleReaction,
} = useContentCard(props, { onLoginRequired: promptLogin });
</script>

<template>
  <article
    class="content-card"
    tabindex="0"
    @click="emit('open', item)"
    @keydown.enter="emit('open', item)"
    @mouseenter="scheduleProviderLoad"
    @mouseleave="cancelProviderLoad"
    @focusin="scheduleProviderLoad"
    @focusout="cancelProviderLoad"
  >
    <div class="poster-wrap">
      <img v-if="item.poster_url" class="poster" :src="item.poster_url" :alt="item.title" loading="lazy" />
      <div v-else class="poster-empty">{{ item.title }}</div>

      <div class="ott-overlay" aria-live="polite">
        <div v-if="providersLoading || providersLoaded" class="ott-panel">
          <span v-if="providersLoading" class="ott-status">확인 중</span>
          <template v-else-if="visibleProviders.length">
            <span class="ott-label">볼 수 있는 곳</span>
            <span
              v-for="provider in visibleProviders"
              :key="`${provider.service}-${provider.type}-${provider.link}`"
              class="ott-icon"
              :title="formatProviderName(provider)"
            >
              <img v-if="provider.icon_url" :src="provider.icon_url" :alt="formatProviderName(provider)" />
              <span v-else>{{ providerInitial(provider) }}</span>
            </span>
          </template>
          <span v-else-if="providersLoaded && !providerError" class="ott-status">OTT 정보 없음</span>
        </div>
      </div>
    </div>

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
      <div class="card-reactions" @click.stop @keydown.stop>
        <button
          class="reaction-icon-button"
          :class="{ active: reactions.my_reaction === 'like' }"
          type="button"
          :disabled="reactionLoading"
          aria-label="좋아요"
          title="좋아요"
          @click="toggleReaction('like')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3v11ZM9 21.9V11.2l4.9-8.1a2.1 2.1 0 0 1 3.8 1.6l-.9 5.3H20a2 2 0 0 1 1.9 2.4l-1.4 7A3 3 0 0 1 17.6 22H9Z" /></svg>
        </button>
        <button
          class="reaction-icon-button"
          :class="{ active: reactions.my_reaction === 'dislike' }"
          type="button"
          :disabled="reactionLoading"
          aria-label="싫어요"
          title="싫어요"
          @click="toggleReaction('dislike')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 2h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3V2ZM15 2.1v10.7l-4.9 8.1a2.1 2.1 0 0 1-3.8-1.6l.9-5.3H4a2 2 0 0 1-1.9-2.4l1.4-7A3 3 0 0 1 6.4 2H15Z" /></svg>
        </button>
      </div>
      <span v-if="reactionMessage" class="reaction-help">{{ reactionMessage }}</span>
    </div>
  </article>
</template>

<style scoped>
.poster-wrap {
  position: relative;
  overflow: hidden;
}

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

.card-reactions {
  display: flex;
  gap: 8px;
  margin-top: 2px;
}

.reaction-icon-button {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 34px;
  border: 1px solid var(--ws-border);
  border-radius: 8px;
  background: var(--ws-surface-2);
  color: var(--ws-text);
  cursor: pointer;
}

.reaction-icon-button svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.reaction-icon-button:hover,
.reaction-icon-button.active {
  border-color: var(--ws-primary);
  background: rgba(198, 243, 73, 0.12);
  color: var(--ws-primary);
}

.reaction-icon-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.reaction-help {
  color: var(--ws-muted);
  font-size: 12px;
  font-weight: 800;
}

.ott-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  padding: 12px;
  background: linear-gradient(180deg, rgba(18, 26, 36, 0.08), rgba(18, 26, 36, 0.86));
  opacity: 0;
  transition: opacity 160ms ease;
  pointer-events: none;
}

.content-card:hover .ott-overlay,
.content-card:focus-within .ott-overlay {
  opacity: 1;
}

.ott-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  align-content: flex-start;
  width: 100%;
  gap: 8px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 8px;
  background: rgba(10, 14, 20, 0.9);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.38);
}

.ott-status {
  display: grid;
  width: 100%;
  place-items: center;
  text-align: center;
}

.ott-label,
.ott-status {
  color: #fff;
  font-size: 13px;
  font-weight: 900;
}

.ott-label {
  width: 100%;
}

.ott-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  overflow: hidden;
  border: 2px solid #fff;
  border-radius: 8px;
  background: #fff;
  color: #26323d;
  font-size: 14px;
  font-weight: 900;
}

.ott-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
