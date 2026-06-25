<script setup>
import { computed, watch } from 'vue';
import { useContentReaction } from '../composables/useContentReaction';

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  mediaType: {
    type: String,
    required: true,
  },
  initialReactions: {
    type: Object,
    default: null,
  },
  onLoginRequired: {
    type: Function,
    default: null,
  },
});

const {
  reactions,
  reactionLoading,
  reactionMessage,
  syncReactions,
  toggleReaction,
} = useContentReaction({ onLoginRequired: () => props.onLoginRequired?.() });

watch(() => props.initialReactions, (value) => syncReactions(value), { immediate: true });

function onToggle(reaction) {
  toggleReaction(reaction, props.item, props.mediaType);
}
</script>

<template>
  <div class="content-reactions">
    <button
      class="reaction-icon-button like"
      :class="{ active: reactions.my_reaction === 'like' }"
      type="button"
      :disabled="reactionLoading"
      aria-label="좋아요"
      title="좋아요"
      @click="onToggle('like')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3v11ZM9 21.9V11.2l4.9-8.1a2.1 2.1 0 0 1 3.8 1.6l-.9 5.3H20a2 2 0 0 1 1.9 2.4l-1.4 7A3 3 0 0 1 17.6 22H9Z" /></svg>
    </button>
    <button
      class="reaction-icon-button dislike"
      :class="{ active: reactions.my_reaction === 'dislike' }"
      type="button"
      :disabled="reactionLoading"
      aria-label="싫어요"
      title="싫어요"
      @click="onToggle('dislike')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 2h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3V2ZM15 2.1v10.7l-4.9 8.1a2.1 2.1 0 0 1-3.8-1.6l.9-5.3H4a2 2 0 0 1-1.9-2.4l1.4-7A3 3 0 0 1 6.4 2H15Z" /></svg>
    </button>
    <span v-if="reactionMessage" class="reaction-help">{{ reactionMessage }}</span>
  </div>
</template>

<style scoped>
.content-reactions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.reaction-icon-button {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 34px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  cursor: pointer;
}

.reaction-icon-button svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.reaction-icon-button.like:hover,
.reaction-icon-button.like.active {
  border-color: var(--ws-primary);
  background: rgba(var(--ws-primary-rgb), 0.24);
  color: #fff;
}

.reaction-icon-button.dislike:hover,
.reaction-icon-button.dislike.active {
  border-color: var(--ws-secondary);
  background: rgba(var(--ws-secondary-rgb), 0.24);
  color: #fff;
}

.reaction-icon-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.reaction-help {
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  font-weight: 800;
}
</style>
