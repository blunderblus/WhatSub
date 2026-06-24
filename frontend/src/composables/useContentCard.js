import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { fetchStreamingProviders, updateContentReaction } from '../api/contents';
import { useSessionStore } from '../stores/session';
import { uniqueProvidersByPlatform } from '../utils/streamingProviders';

const EMPTY_REACTIONS = { like_count: 0, dislike_count: 0, my_reaction: null };
const MIN_PROVIDER_LOADING_MS = 550;

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export function useContentCard(props, options = {}) {
  const session = useSessionStore();
  const providers = ref([]);
  const providersLoaded = ref(false);
  const providersLoading = ref(false);
  const providerError = ref('');
  const reactions = ref(EMPTY_REACTIONS);
  const reactionLoading = ref(false);
  const reactionMessage = ref('');
  const hoverTimer = ref(null);

  const resolvedMediaType = computed(() => props.mediaType || props.item.media_type || 'movie');
  const visibleProviders = computed(() => uniqueProvidersByPlatform(providers.value).slice(0, 6));

  function syncReactions() {
    reactions.value = props.item.reactions || EMPTY_REACTIONS;
    reactionMessage.value = '';
  }

  async function loadProviders() {
    if (providersLoaded.value || providersLoading.value || !props.item.tmdb_id) return;

    providersLoading.value = true;
    providerError.value = '';
    const loadingStartedAt = Date.now();
    try {
      providers.value = await fetchStreamingProviders({
        tmdbId: props.item.tmdb_id,
        mediaType: resolvedMediaType.value,
      });
      providersLoaded.value = true;
    } catch (err) {
      providerError.value = err.message;
      providersLoaded.value = true;
    } finally {
      const elapsed = Date.now() - loadingStartedAt;
      if (elapsed < MIN_PROVIDER_LOADING_MS) {
        await wait(MIN_PROVIDER_LOADING_MS - elapsed);
      }
      providersLoading.value = false;
    }
  }

  function scheduleProviderLoad() {
    if (providersLoaded.value || providersLoading.value) return;
    cancelProviderLoad();
    hoverTimer.value = setTimeout(() => {
      hoverTimer.value = null;
      loadProviders();
    }, 450);
  }

  function cancelProviderLoad() {
    if (!hoverTimer.value) return;
    clearTimeout(hoverTimer.value);
    hoverTimer.value = null;
  }

  async function toggleReaction(reaction) {
    reactionMessage.value = '';
    if (!session.isAuthenticated) {
      options.onLoginRequired?.();
      return;
    }

    reactionLoading.value = true;
    try {
      reactions.value = await updateContentReaction({
        tmdbId: props.item.tmdb_id,
        mediaType: resolvedMediaType.value,
        reaction,
        title: props.item.title || '',
        posterUrl: props.item.poster_url || '',
      });
    } catch (err) {
      reactionMessage.value = err.message;
    } finally {
      reactionLoading.value = false;
    }
  }

  watch(() => props.item, syncReactions, { immediate: true });
  onBeforeUnmount(cancelProviderLoad);

  return {
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
  };
}
