import { ref } from 'vue';
import { updateContentReaction } from '../api/contents';
import { useSessionStore } from '../stores/session';

export const EMPTY_REACTIONS = { like_count: 0, dislike_count: 0, my_reaction: null };

export function useContentReaction(options = {}) {
  const session = useSessionStore();
  const reactions = ref({ ...EMPTY_REACTIONS });
  const reactionLoading = ref(false);
  const reactionMessage = ref('');

  function syncReactions(next = EMPTY_REACTIONS) {
    reactions.value = next || { ...EMPTY_REACTIONS };
    reactionMessage.value = '';
  }

  async function toggleReaction(reaction, item, mediaType) {
    reactionMessage.value = '';
    if (!item?.tmdb_id) return;

    if (!session.isAuthenticated) {
      options.onLoginRequired?.();
      return;
    }

    reactionLoading.value = true;
    try {
      reactions.value = await updateContentReaction({
        tmdbId: item.tmdb_id,
        mediaType,
        reaction,
        title: item.title || '',
        posterUrl: item.poster_url || '',
      });
    } catch (err) {
      reactionMessage.value = err.message;
    } finally {
      reactionLoading.value = false;
    }
  }

  return {
    reactions,
    reactionLoading,
    reactionMessage,
    syncReactions,
    toggleReaction,
  };
}
